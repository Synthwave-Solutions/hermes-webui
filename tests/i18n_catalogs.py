"""Execute the shipped locale registrations rather than parsing JS source."""
from functools import lru_cache
import json
from pathlib import Path
import subprocess


@lru_cache(maxsize=1)
def locale_catalogs():
    script = """
const fs = require('fs'), vm = require('vm');
const directory = process.argv[1], catalogs = {};
const window = {};
const context = vm.createContext({window, URL, console, location:{href:'http://localhost/'},
  document:{currentScript:null, baseURI:'http://localhost/', documentElement:{},
    createElement:()=>({}), head:{appendChild(){}}, querySelectorAll:()=>[]}});
vm.runInContext(fs.readFileSync(directory + '/../i18n.js', 'utf8'), context);
const register = window.__registerHermesLocale;
window.__registerHermesLocale = (name, values) => { catalogs[name] = values; register(name, values); };
for (const name of fs.readdirSync(directory).filter(n => n.endsWith('.js'))) {
  vm.runInContext(fs.readFileSync(directory + '/' + name, 'utf8'), context);
}
process.stdout.write(JSON.stringify(catalogs));
"""
    root = Path(__file__).resolve().parent.parent / "static/i18n"
    return json.loads(subprocess.check_output(["node", "-e", script, str(root)], text=True))
