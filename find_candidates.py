#!/usr/bin/env python3
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime

MODULES = ["./mavlink", "./commander"]
CAND_DIR = Path("candidates")
CAND_DIR.mkdir(exist_ok=True)

PATTERN = r"(?i)\b(debug|test|factory|failsafe|maintenance|hidden|emergency|stream|parameter|mode|transition|command|arm|disarm)\b"

def extract_function_block(file_path: Path, target_line: int) -> str:
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    if target_line < 0 or target_line >= len(lines):
        return ""
    
    start = target_line
    brace_count = 0
    for i in range(target_line, max(0, target_line - 40), -1):
        line = lines[i]
        brace_count += line.count('{') - line.count('}')
        if line.strip().endswith('{') and brace_count == 0:
            start = i
            break
            
    end = target_line
    brace_count = 0
    for i in range(target_line, min(len(lines), target_line + 100)):
        brace_count += lines[i].count('{') - lines[i].count('}')
        if brace_count <= 0 and i > target_line:
            end = i
            break
            
    return "".join(lines[start:end+1])

def main():
    print("[*] Starting candidate search (Stage 1)...")
    found_total = 0
    
    commander_final_txt = CAND_DIR / "commander_candidates_all.txt"
    mavlink_final_txt = CAND_DIR / "mavlink_candidates_all.txt"
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commander_final_txt.write_text(f"=== ANALYSIS CANDIDATE COLLECTION: MOD_COMMANDER ({timestamp}) ===\n\n", encoding="utf-8")
    mavlink_final_txt.write_text(f"=== ANALYSIS CANDIDATE COLLECTION: MOD_MAVLINK ({timestamp}) ===\n\n", encoding="utf-8")
    
    for mod in MODULES:
        mod_path = Path(mod)
        if not mod_path.is_dir():
            print(f"  {mod} not found, skipping")
            continue
            
        mod_clean_name = mod.strip('./')
        print(f"\n[*] Analyzing {mod}...")
        
        target_output_file = mavlink_final_txt if mod_clean_name == "mavlink" else commander_final_txt
        
        cmd = ["rg", "-n", "-i", "-e", PATTERN, str(mod_path), "--glob", "*.cpp", "--glob", "*.c", "--glob", "*.h"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            matches = [m for m in res.stdout.strip().split('\n') if m]
        except subprocess.CalledProcessError:
            print("  (No matches found or rg is not installed)")
            continue
            
        processed = set()
        mod_found = 0
        
        for m in matches:
            parts = m.split(':', 2)
            if len(parts) < 2: continue
            fpath_str, lnum = parts[0], int(parts[1]) - 1
            fpath = Path(fpath_str)
            
            key = f"{fpath}_{lnum}"
            if key in processed: continue
            processed.add(key)
            
            block = extract_function_block(fpath, lnum)
            if not block.strip(): continue
            
            func_entry_tag = (
                f"\n"
                f"[START_CANDIDATE_BLOCK] ====================================================\n"
                f"SOURCE-FILE: {fpath.name}\n"
                f"FULL-PATH: {fpath}\n"
                f"HEURISTIC-MATCH-LINE: {lnum + 1}\n"
                f"------------------------------------------------------------------------\n"
                f"FUNCTION-SOURCE-CODE:\n"
            )
            
            func_exit_tag = (
                f"\n"
                f"------------------------------------------------------------------------\n"
                f"[END_CANDIDATE_BLOCK] ======================================================\n"
            )
            
            with open(target_output_file, 'a', encoding='utf-8') as f:
                f.write(func_entry_tag)
                f.write(block)
                f.write(func_exit_tag)
                
            mod_found += 1
            found_total += 1
            
        print(f"  [+] Module {mod_clean_name}: found and recorded {mod_found} candidate functions.")
            
    print(f"\n[+] Done. All {found_total} candidates saved into two consolidated files:")
    print(f"  1. {commander_final_txt}")
    print(f"  2. {mavlink_final_txt}")

if __name__ == "__main__":
    main()