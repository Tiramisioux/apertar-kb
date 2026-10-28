// Extracts the WebUI page from WebControlPage.cpp (between R"APERTAR( and )APERTAR") and its inline script.
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const page = src.slice(src.indexOf('R"APERTAR(') + 'R"APERTAR('.length, src.indexOf(')APERTAR"'));
fs.writeFileSync(process.argv[3], page);
if (process.argv[4]) {
  const script = page.slice(page.indexOf("<script>") + 8, page.lastIndexOf("</script>"));
  fs.writeFileSync(process.argv[4], script);
}
