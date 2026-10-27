// Host-side simulation of the PiSP BE configuration libcamera-apertar builds for
// IMX585 Clear HDR 16-bit 3840x2200 + one YUV420 preview stream on output 1.
// Mirrors configureBe()/platformConfigure() in pisp.cpp and the IPA enables.
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <string>

#include "backend/backend.hpp"
#include "common/utils.hpp"
#include "variants/variant.hpp"

using namespace libpisp;

struct Case {
	const char *name;
	int outW, outH;           // preview size
	int cropX, cropY, cropW, cropH; // BE crop for output 1
	bool tdn;                 // TDN in/out enabled
	int inW, inH;             // BE input size
	bool rgb_out;             // false: YUV420
};

static void run(const Case &c)
{
	const PiSPVariant &v = BCM2712_D0;
	BackEnd be(BackEnd::Config({}), v);

	pisp_image_format_config in = {};
	in.width = c.inW;
	in.height = c.inH;
	in.format = PISP_IMAGE_FORMAT_BPS_16 + PISP_IMAGE_FORMAT_UNCOMPRESSED;
	compute_optimal_stride(in);

	pisp_be_global_config g;
	be.GetGlobal(g);
	g.bayer_enables = PISP_BE_BAYER_ENABLE_INPUT | PISP_BE_BAYER_ENABLE_DEMOSAIC |
			  PISP_BE_BAYER_ENABLE_BLC | PISP_BE_BAYER_ENABLE_WBG |
			  PISP_BE_BAYER_ENABLE_DPC | PISP_BE_BAYER_ENABLE_GEQ |
			  PISP_BE_BAYER_ENABLE_SDN | PISP_BE_BAYER_ENABLE_CDN |
			  PISP_BE_BAYER_ENABLE_LSC;
	if (c.tdn)
		g.bayer_enables |= PISP_BE_BAYER_ENABLE_TDN | PISP_BE_BAYER_ENABLE_TDN_OUTPUT |
				   PISP_BE_BAYER_ENABLE_TDN_INPUT;
	g.rgb_enables = PISP_BE_RGB_ENABLE_YCBCR | PISP_BE_RGB_ENABLE_YCBCR_INVERSE |
			PISP_BE_RGB_ENABLE_FALSE_COLOUR | PISP_BE_RGB_ENABLE_GAMMA |
			PISP_BE_RGB_ENABLE_CCM | PISP_BE_RGB_ENABLE_SHARPEN |
			PISP_BE_RGB_ENABLE_CSC1 | PISP_BE_RGB_ENABLE_OUTPUT1;
	g.bayer_order = PISP_BAYER_ORDER_RGGB;

	pisp_be_output_format_config o = {};
	o.image.width = c.outW;
	o.image.height = c.outH;
	if (c.rgb_out) {
		o.image.format = PISP_IMAGE_FORMAT_THREE_CHANNEL;
	} else {
		o.image.format = PISP_IMAGE_FORMAT_THREE_CHANNEL + PISP_IMAGE_FORMAT_BPS_8 +
				 PISP_IMAGE_FORMAT_SAMPLING_420 + PISP_IMAGE_FORMAT_PLANARITY_PLANAR;
	}
	compute_optimal_stride(o.image);
	if (!c.rgb_out)
		o.image.stride = o.image.stride2 * 2; // as computeOptimalStride() in pisp.cpp
	o.lo = 16 << 8; o.hi = 235 << 8; o.lo2 = 16 << 8; o.hi2 = 240 << 8;

	BackEnd::SmartResize r = {};
	r.width = c.outW;
	r.height = c.outH;
	be.SetSmartResize(1, r);
	pisp_be_crop_config crop = { (uint16_t)c.cropX, (uint16_t)c.cropY, (uint16_t)c.cropW, (uint16_t)c.cropH };
	be.SetCrop(1, crop);
	be.SetOutputFormat(1, o);

	be.SetTdnOutputFormat(in);
	be.SetTdnInputFormat(in);
	be.SetStitchOutputFormat(in);
	be.SetStitchInputFormat(in);

	be.SetGlobal(g);
	be.SetInputFormat(in);

	static pisp_be_tiles_config cfg;
	memset(&cfg, 0, sizeof(cfg));
	be.Prepare(&cfg);

	pisp_be_global_config gg = cfg.config.global;
	printf("== %s\n", c.name);
	printf("input %ux%u stride %u ; output1 %ux%u stride %u stride2 %u\n", in.width, in.height, in.stride,
	       cfg.config.output_format[1].image.width, cfg.config.output_format[1].image.height,
	       cfg.config.output_format[1].image.stride, cfg.config.output_format[1].image.stride2);
	printf("bayer_enables 0x%06x rgb_enables 0x%06x  downscale1 %s resample1 %s\n", gg.bayer_enables,
	       gg.rgb_enables, (gg.rgb_enables & PISP_BE_RGB_ENABLE_DOWNSCALE1) ? "on" : "off",
	       (gg.rgb_enables & PISP_BE_RGB_ENABLE_RESAMPLE1) ? "on" : "off");
	printf("num_tiles %u\n", cfg.num_tiles);
	unsigned long long inPix = 0, outPix = 0;
	for (unsigned i = 0; i < cfg.num_tiles; i++) {
		const pisp_tile &t = cfg.tiles[i];
		printf("  tile %2u in x=%4u y=%4u w=%3u h=%4u  out1 x=%4u y=%4u w=%4u h=%4u\n", i, t.input_offset_x,
		       t.input_offset_y, t.input_width, t.input_height, t.output_offset_x[1], t.output_offset_y[1],
		       t.output_width[1], t.output_height[1]);
		inPix += (unsigned long long)t.input_width * t.input_height;
		outPix += (unsigned long long)t.output_width[1] * t.output_height[1];
	}
	double frame = (double)in.width * in.height;
	double inBytes = inPix * 2.0;
	double outBytes = outPix * 1.5;
	printf("tile input pixels %llu = %.4f x frame (%.0f) ; input bytes read %.3f MB\n", inPix, inPix / frame, frame,
	       inBytes / 1e6);
	double tdnR = (gg.bayer_enables & PISP_BE_BAYER_ENABLE_TDN_INPUT) ? inBytes : 0;
	double tdnW = (gg.bayer_enables & PISP_BE_BAYER_ENABLE_TDN_OUTPUT) ? inBytes : 0;
	printf("TDN read %.3f MB, TDN write %.3f MB (tile regions, 16-bit uncompressed)\n", tdnR / 1e6, tdnW / 1e6);
	printf("output1 bytes %.3f MB\n", outBytes / 1e6);
	double total = inBytes + tdnR + tdnW + outBytes;
	printf("TOTAL BE traffic %.3f MB/frame = %.3f GB/s at 30 fps\n\n", total / 1e6, total * 30 / 1e9);
}

int main()
{
	Case cases[] = {
		{ "A: as configured (3840x2200 in, crop 0,20 3840x2160, YUV420 1280x720, TDN on)", 1280, 720, 0, 20, 3840, 2160, true, 3840, 2200, false },
		{ "B: TDN off", 1280, 720, 0, 20, 3840, 2160, false, 3840, 2200, false },
		{ "C: TDN on, preview 640x360", 640, 360, 0, 20, 3840, 2160, true, 3840, 2200, false },
		{ "D: TDN on, crop 1920x1080 centre (2x ScalerCrop zoom), 1280x720", 1280, 720, 960, 560, 1920, 1080, true, 3840, 2200, false },
		{ "E: TDN on, BE input 1920x1100 (hypothetical half-size Bayer), 1280x720", 1280, 720, 0, 10, 1920, 1080, true, 1920, 1100, false },
		{ "F: TDN off, BE input 1920x1100 (hypothetical half-size Bayer), 1280x720", 1280, 720, 0, 10, 1920, 1080, false, 1920, 1100, false },
	};
	for (auto &c : cases) {
		try {
			run(c);
		} catch (std::exception &e) {
			printf("== %s\nEXCEPTION %s\n\n", c.name, e.what());
		}
	}
	return 0;
}
