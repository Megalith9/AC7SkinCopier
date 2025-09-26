import json
import os
import re
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

CONFIG_FILE = "config.json"

# ---------------- UAssetGUI path configuration ----------------
def save_config(exe_path):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"uassetgui_path": exe_path}, f)
    except Exception as e:
        print(f"⚠️ Could not save configuration: {e}")


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("uassetgui_path", "")
        except Exception as e:
            print(f"⚠️ Could not read configuration: {e}")
    return ""

# ---------------- Pattern replacement in JSON ----------------
def replace_patterns(data, old_xxxx, new_xxxx, old_yy, new_yy):
    replacements = [
        (rf"\bAcePlayerPawn_{old_xxxx}_s{old_yy}\b", f"AcePlayerPawn_{new_xxxx}_s{new_yy}"),
        (rf"\bAcePlayerPawn_{old_xxxx}\b", f"AcePlayerPawn_{new_xxxx}"),
        (rf"/Game/Blueprint/Player/Pawn/AcePlayerPawn_{old_xxxx}_s{old_yy}", f"/Game/Blueprint/Player/Pawn/AcePlayerPawn_{new_xxxx}_s{new_yy}"),
        (rf"/Game/Blueprint/Player/Pawn/AcePlayerPawn_{old_xxxx}", f"/Game/Blueprint/Player/Pawn/AcePlayerPawn_{new_xxxx}"),
        (rf"/Game/Blueprint/Player/Pawn/Skin/AcePlayerPawn_{old_xxxx}_s{old_yy}", f"/Game/Blueprint/Player/Pawn/Skin/AcePlayerPawn_{new_xxxx}_s{new_yy}"),
        (rf"/Game/Vehicles/Aircraft/{old_xxxx}/{old_yy}/{old_xxxx}_{old_yy}_CP_Inst", f"/Game/Vehicles/Aircraft/{new_xxxx}/{new_yy}/{new_xxxx}_{new_yy}_CP_Inst"),
        (rf"/Game/Vehicles/Aircraft/{old_xxxx}/{old_yy}/{old_xxxx}_{old_yy}_Decal_Inst", f"/Game/Vehicles/Aircraft/{new_xxxx}/{new_yy}/{new_xxxx}_{new_yy}_Decal_Inst"),
        (rf"/Game/Vehicles/Aircraft/{old_xxxx}/{old_yy}/{old_xxxx}_{old_yy}_Inst", f"/Game/Vehicles/Aircraft/{new_xxxx}/{new_yy}/{new_xxxx}_{new_yy}_Inst"),
        (rf"\b{old_xxxx}_{old_yy}_CP_Inst\b", f"{new_xxxx}_{new_yy}_CP_Inst"),
        (rf"\b{old_xxxx}_{old_yy}_Decal_Inst\b", f"{new_xxxx}_{new_yy}_Decal_Inst"),
        (rf"\b{old_xxxx}_{old_yy}_Inst\b", f"{new_xxxx}_{new_yy}_Inst"),
        (rf"\bAcePlayerPawn_{old_xxxx}_s{old_yy}_C\b", f"AcePlayerPawn_{new_xxxx}_s{new_yy}_C"),
        (rf"\bAcePlayerPawn_{old_xxxx}_C\b", f"AcePlayerPawn_{new_xxxx}_C"),
        (rf"\bDefault__AcePlayerPawn_{old_xxxx}_s{old_yy}_C\b", f"Default__AcePlayerPawn_{new_xxxx}_s{new_yy}_C"),
        (rf"\bDefault__AcePlayerPawn_{old_xxxx}_C\b", f"Default__AcePlayerPawn_{new_xxxx}_C"),
    ]
    compiled = [(re.compile(p), r) for p, r in replacements]

    def replace_str(s):
        for pattern, repl in compiled:
            s = pattern.sub(repl, s)
        return s

    if "NameMap" in data:
        data["NameMap"] = [replace_str(s) for s in data["NameMap"]]

    if "Imports" in data:
        for imp in data["Imports"]:
            if "ObjectName" in imp:
                imp["ObjectName"] = replace_str(imp["ObjectName"])
            if "ClassPackage" in imp and imp["ClassPackage"]:
                imp["ClassPackage"] = replace_str(imp["ClassPackage"])
            if "ClassName" in imp and imp["ClassName"]:
                imp["ClassName"] = replace_str(imp["ClassName"])

    if "Exports" in data:
        for exp in data["Exports"]:
            if "ObjectName" in exp:
                exp["ObjectName"] = replace_str(exp["ObjectName"])
            if "Data" in exp and isinstance(exp["Data"], list):
                for d in exp:
                    if isinstance(d, dict) and "Value" in d and isinstance(d["Value"], str):
                        d["Value"] = replace_str(d["Value"])
    return data

# ---------------- Detect old IDs ----------------
def detect_old_ids(original_data):
    search_space = []
    search_space.extend(original_data.get("NameMap", []))
    for imp in original_data.get("Imports", []):
        if "ObjectName" in imp:
            search_space.append(imp["ObjectName"])
    for exp in original_data.get("Exports", []):
        if "ObjectName" in exp:
            search_space.append(exp["ObjectName"])
    text = " ".join(search_space)
    match = re.search(r"AcePlayerPawn_(\w+)_s(\d+)", text)
    if match:
        return match.group(1), match.group(2)
    return None, None

# ---------------- Convert to UAsset/UEXP ----------------
def convert_with_uassetgui(json_path, exe_path, log_widget):
    dest_path = json_path.replace(".json", ".uasset")
    try:
        log_widget.insert(tk.END, f"Converting {os.path.basename(json_path)}...\n")
        log_widget.see(tk.END)
        subprocess.run([exe_path, "fromjson", json_path, dest_path], check=True)
        log_widget.insert(tk.END, f"✅ Converted to {os.path.basename(dest_path)} (+ .uexp)\n")
        log_widget.see(tk.END)
    except subprocess.CalledProcessError as e:
        log_widget.insert(tk.END, f"❌ Error converting {json_path}: {e}\n")
        log_widget.see(tk.END)

# ---------------- Prepare input (accept .json or .uasset) ----------------
def prepare_input_file(filepath, exe_path, log_widget, engine_version="23", mappings=None):
    """
    Ensures we always get a JSON file back.
    If the input is .json -> return as-is.
    If the input is .uasset -> convert it to JSON via UAssetGUI.
    """
    if filepath.lower().endswith(".json"):
        return filepath  # Already JSON

    if filepath.lower().endswith(".uasset"):
        temp_json = filepath.replace(".uasset", "_temp.json")
        cmd = [exe_path, "tojson", filepath, temp_json, engine_version]
        if mappings:
            cmd.append(mappings)

        try:
            log_widget.insert(tk.END, f"Converting {os.path.basename(filepath)} to JSON...\n")
            log_widget.see(tk.END)
            subprocess.run(cmd, check=True)
            log_widget.insert(tk.END, f"✅ Converted to {os.path.basename(temp_json)}\n")
            log_widget.see(tk.END)
            return temp_json
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to convert {filepath} to JSON:\n{e}")
            return None

    messagebox.showerror("Error", f"Unsupported file type: {filepath}")
    return None

# ---------------- Main JSON processing ----------------
def process_json_file(filepath, new_xxxx, yy_start, yy_end, exe_path, log_widget, progress_bar):
    with open(filepath, "r", encoding="utf-8") as f:
        original_data = json.load(f)

    old_xxxx, old_yy = detect_old_ids(original_data)
    if not old_xxxx or not old_yy:
        messagebox.showerror("Error", "Could not detect the PlaneID and SkinID pattern in the file.")
        return

    total = int(yy_end) - int(yy_start) + 1
    progress_bar["maximum"] = total
    progress_bar["value"] = 0

    for idx, yy in enumerate(range(int(yy_start), int(yy_end) + 1), start=1):
        new_yy = f"{yy:02d}"
        new_data = json.loads(json.dumps(original_data))
        new_data = replace_patterns(new_data, old_xxxx, new_xxxx, old_yy, new_yy)

        new_filename = f"AcePlayerPawn_{new_xxxx}_s{new_yy}.json"
        out_path = os.path.join(os.path.dirname(filepath), new_filename)

        if os.path.exists(out_path):
            out_path = out_path.replace(".json", "_new.json")

        with open(out_path, "w", encoding="utf-8") as out_f:
            json.dump(new_data, out_f, indent=2, ensure_ascii=False)

        log_widget.insert(tk.END, f"Generated JSON: {os.path.basename(out_path)}\n")
        log_widget.see(tk.END)

        convert_with_uassetgui(out_path, exe_path, log_widget)

        # Delete intermediate JSON
        if os.path.exists(out_path):
            try:
                os.remove(out_path)
                log_widget.insert(tk.END, f"🗑️ JSON deleted: {os.path.basename(out_path)}\n")
                log_widget.see(tk.END)
            except Exception as e:
                log_widget.insert(tk.END, f"⚠️ Could not delete {out_path}: {e}\n")
                log_widget.see(tk.END)

        # Update progress bar
        progress_bar["value"] = idx
        progress_bar.update()

    messagebox.showinfo("Done", f"Files generated and converted from s{yy_start} to s{yy_end}.")

# ---------------- GUI ----------------
def select_file(entry):
    filename = filedialog.askopenfilename(filetypes=[("UAsset/JSON files", "*.uasset;*.json")])
    if filename:
        entry.delete(0, tk.END)
        entry.insert(0, filename)

def select_exe(entry):
    filename = filedialog.askopenfilename(filetypes=[("Executable", "*.exe")])
    if filename:
        entry.delete(0, tk.END)
        entry.insert(0, filename)
        save_config(filename)

def main():
    root = tk.Tk()
    root.title("MegaSkinCopier JSON/UAsset Generator")

    tk.Label(root, text="Base file (.json or .uasset):").grid(row=0, column=0, sticky="e")
    entry_file = tk.Entry(root, width=50)
    entry_file.grid(row=0, column=1)
    tk.Button(root, text="Browse...", command=lambda: select_file(entry_file)).grid(row=0, column=2)

    tk.Label(root, text="New PlaneID:").grid(row=1, column=0, sticky="e")
    entry_xxxx = tk.Entry(root)
    entry_xxxx.grid(row=1, column=1)

    tk.Label(root, text="Min SkinID (e.g. 02):").grid(row=2, column=0, sticky="e")
    entry_yy_start = tk.Entry(root)
    entry_yy_start.grid(row=2, column=1)

    tk.Label(root, text="Max SkinID (e.g. 09):").grid(row=3, column=0, sticky="e")
    entry_yy_end = tk.Entry(root)
    entry_yy_end.grid(row=3, column=1)

    tk.Label(root, text="UAssetGUI.exe path:").grid(row=4, column=0, sticky="e")
    entry_exe = tk.Entry(root, width=50)
    entry_exe.grid(row=4, column=1)
    tk.Button(root, text="Browse...", command=lambda: select_exe(entry_exe)).grid(row=4, column=2)

    # Load last saved path automatically
    entry_exe.insert(0, load_config())

    # Progress bar
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
    progress_bar.grid(row=5, column=0, columnspan=3, pady=5)

    # Log box
    log_box = scrolledtext.ScrolledText(root, width=80, height=20, state="normal")
    log_box.grid(row=7, column=0, columnspan=3, padx=5, pady=5)

    def run():
        filepath = entry_file.get()
        new_xxxx = entry_xxxx.get().strip()
        yy_start = entry_yy_start.get().strip()
        yy_end = entry_yy_end.get().strip()
        exe_path = entry_exe.get().strip()

        if not (filepath and new_xxxx and yy_start and yy_end and exe_path):
            messagebox.showerror("Error", "Please complete all fields.")
            return

        if not re.match(r"^[A-Za-z0-9_]+$", new_xxxx):
            messagebox.showerror("Error", "PlaneID must contain only letters, numbers, and underscores.")
            return

        if not yy_start.isdigit() or not yy_end.isdigit():
            messagebox.showerror("Error", "SkinID values must be numbers.")
            return

        if int(yy_start) < 1 or int(yy_end) < int(yy_start):
            messagebox.showerror("Error", "Invalid SkinID range.")
            return

        if not os.path.exists(exe_path):
            messagebox.showerror("Error", "Invalid UAssetGUI.exe path.")
            return

        json_file = prepare_input_file(filepath, exe_path, log_box)
        if json_file:
            process_json_file(json_file, new_xxxx, yy_start, yy_end, exe_path, log_box, progress_bar)
            if json_file.endswith("_temp.json") and os.path.exists(json_file):
                os.remove(json_file)  # Clean up temporary file

    tk.Button(root, text="Generate files", command=run).grid(row=6, column=1, pady=10)
    root.mainloop()


if __name__ == "__main__":
    main()
