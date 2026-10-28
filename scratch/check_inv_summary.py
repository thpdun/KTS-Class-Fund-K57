import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("scratch/detailed_inventory.json", "r", encoding="utf-8") as f:
    d = json.load(f)

print("Unique HTML IDs:", d["unique_html_ids_count"])
print("JS Accessed IDs:", d["js_accessed_ids_count"])
print("IDs in HTML not accessed in JS:", len(d["ids_not_in_js"]))
print("IDs in JS not found in HTML:", len(d["ids_in_js_not_in_html"]))
print("Dynamic onclicks in JS:", len(d["dynamic_onclicks_js"]))
print("Listeners in JS:", len(d["listeners"]))

print("\n--- IDs IN JS NOT IN HTML ---")
print(d["ids_in_js_not_in_html"])

print("\n--- DYNAMIC ONCLICKS IN JS ---")
for doc in d["dynamic_onclicks_js"]:
    print(" ", doc)

print("\n--- ONCLICKS IN HTML MARKUP ---")
for o in d["onclicks_markup"][:10]:
    print(f"  Line {o['line']}: <{o['tag']} id=\"{o['id']}\"> -> {o['onclick']}")
print(f"  ... ({len(d['onclicks_markup'])} total)")
