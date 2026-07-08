# GUI library
import tkinter as tk

# submodules: messagebox => pop-up windows, ttk => themed tk (modern look/widgets)
from tkinter import messagebox, ttk

# allow py to talk to file sys
import os

# allow py to run ext commands (git)
import subprocess

# prevent tool from freezing during a process
import threading

# Variables
h_file = "qb_history.txt"

# ======================================================================================================================
# VALIDATION
# ======================================================================================================================

def validate_fields(*args):
    if folder_var.get().strip() and url_var.get().strip():
        init_button.config(state="normal")
    else:
        init_button.config(state="disabled")

    if folder_var.get().strip() and msg_var.get().strip():
        anc_button.config(state="normal")
        push_button.config(state="normal")
        sync_button.config(state="normal")
    else:
        anc_button.config(state="disabled")
        push_button.config(state="disabled")
        sync_button.config(state="disabled")

def validate_environment(folder_name, check_git=True):
    if not os.path.isdir(folder_name):
        messagebox.showerror("Error", f"Path '{folder_name}' is not a valid directory.")
        return False
    if check_git:
        result = subprocess.run(['git', '-C', folder_name, 'rev-parse', '--is-inside-work-tree'],
                                capture_output=True, text=True)
        if result.returncode != 0:
            messagebox.showerror("Error", "Not a Git repository. Initialize it first.")
            return False
    return True

# ======================================================================================================================
# COMMANDS
# ======================================================================================================================

def init_new_repo():
    folder = folder_entry.get().strip()
    url = url_entry.get().strip()

    update_btns("disabled")
    update_sts(init_button.config, text="Processing...")

    try:
        if not folder or not url:
            update_sts(messagebox.showwarning, title="Input", message="Please enter both folder path and GitHub URL!")
            return

        commands = [
            ['git', '-C', folder, 'init'],
            ['git', '-C', folder, 'add', '.'],
            ['git', '-C', folder, 'commit', '-m', 'Initial commit'],
            ['git', '-C', folder, 'branch', '-M', 'main'],
            ['git', '-C', folder, 'remote', 'add', 'origin', url],
            ['git', '-C', folder, 'push', '-u', 'origin', 'main']
        ]

        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                update_sts(messagebox.showerror, title="Git Error", message=f"Failed at: {' '.join(cmd)}\n{result.stderr}")
                return

        save_history(folder)
        set_status("CONNECTED TO GITHUB")

    finally:
        update_btns("normal")
        validate_fields()
        update_sts(init_button.config, text="Initialize & Push")

def do_all():
    folder = folder_entry.get().strip()
    branch = branch_var.get().strip()
    msg = commit_entry.get().strip()

    update_btns("disabled")
    update_sts(sync_button.config, text="Processing...")

    try:
        if not folder or not msg:
            update_sts(messagebox.showwarning, title="Input", message="Please fill up all entry fields.")
            return

        if not branch:
            branch = "main"
            branch_var.set("main")

        checkout_res = subprocess.run(['git', '-C', folder, 'checkout', branch], capture_output=True, text=True)
        if checkout_res.returncode != 0:
            create_res = subprocess.run(['git', '-C', folder, 'checkout', '-b', branch], capture_output=True, text=True)
            if create_res.returncode != 0:
                update_sts(messagebox.showerror, title="Git Error",
                           message=f"Could not create to branch '{branch}':\n{checkout_res.stderr}")
                return
            else:
                set_status(f"CREATED % SWITCHED TO BRANCH: {branch}")
        else:
            set_status(f"SWITCHED TO BRANCH: {branch}")

        status = subprocess.run(['git', '-C', folder, 'status', '--porcelain'], capture_output=True, text=True)
        if not status.stdout.strip():
            update_sts(messagebox.showinfo, title="Status", message="No changes detected.")
            return

        commands = [
            ['git', '-C', folder, 'add', '.'],
            ['git', '-C', folder, 'commit', '-m', msg],
            ['git', '-C', folder, 'push', '-u', 'origin', branch]
        ]

        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                update_sts(messagebox.showerror, title="Git Error", message="Failed!")
                return

        save_history(folder)
        set_status("REPOSITORY UPDATED")

    finally:
        update_btns("normal")
        validate_fields()
        update_sts(sync_button.config, text="Do All")

def commit_changes():
    folder = folder_entry.get().strip()
    msg = commit_entry.get().strip()

    update_btns("disabled")
    update_sts(anc_button.config, text="Processing...")

    try:
        if not msg:
            update_sts(messagebox.showwarning, title="Input", message="Please enter a commit message!")
            return

        if not validate_environment(folder): return

        status = subprocess.run(['git', '-C', folder, 'status', '--porcelain'], capture_output=True, text=True)
        if not status.stdout.strip():
            update_sts(messagebox.showinfo, title="Status", message="No changes detected.")
            return

        subprocess.run(['git', '-C', folder, 'add', '.'])
        result = subprocess.run(['git', '-C', folder, 'commit', '-m', msg], capture_output=True, text=True)

        if result.returncode == 0:
            set_status("READY TO PUSH")
        else:
            update_sts(messagebox.showerror, title="Git Error", message=result.stderr)

    finally:
        update_btns("normal")
        validate_fields()
        update_sts(anc_button.config, text="Add & Commit")

def push_to_github():
    folder = folder_entry.get().strip()
    branch = branch_var.get().strip()

    update_btns("disabled")
    update_sts(push_button.config, text="Processing...")

    try:
        if not validate_environment(folder): return

        if not branch:
            branch = "main"
            branch_var.set("main")

        checkout_res = subprocess.run(['git', '-C', folder, 'checkout', branch], capture_output=True, text=True)
        if checkout_res.returncode != 0:
            create_res = subprocess.run(['git', '-C', folder, 'checkout', '-b', branch], capture_output=True, text=True)
            if create_res.returncode != 0:
                update_sts(messagebox.showerror, title="Git Error", message=f"Could not create to branch '{branch}':\n{checkout_res.stderr}")
                return
            else:
                set_status(f"CREATED % SWITCHED TO BRANCH: {branch}")
        else:
            set_status(f"SWITCHED TO BRANCH: {branch}")

        status = subprocess.run(['git', '-C', folder, 'status', '--porcelain'], capture_output=True, text=True)
        if status.stdout.strip():
            update_sts(messagebox.showerror, title="Push Blocked", message="Uncommitted changes detected! Please commit them first.")
            return

        result = subprocess.run(['git', '-C', folder, 'push', '-u', 'origin', branch], capture_output=True, text=True)
        if result.returncode == 0:
            save_history(folder)
            set_status("REPOSITORY UPDATED")
        else:
            update_sts(messagebox.showerror, title="Push Failed", message=result.stderr)

    finally:
        update_btns("normal")
        validate_fields()
        update_sts(push_button.config, text="Push to GitHub")

# ======================================================================================================================
# HISTORY
# ======================================================================================================================

def load_history():
    if os.path.exists(h_file):
        with open(h_file, 'r') as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

def save_history(path):
    history = load_history()

    if path in history:
        history.remove(path)
    history.insert(0, path)
    history = history[:5]

    with open(h_file, 'w') as f:
        f.write('\n'.join(history))
    folder_entry['values'] = history

# ======================================================================================================================
# HELPERS
# ======================================================================================================================

# threading
def run_async(func):
    threading.Thread(target=func, daemon=True).start()

# process status
def update_sts(func, **kwargs):
    root.after(0, lambda: func(**kwargs))

# button status
def update_btns(state):
    buttons = [init_button, anc_button, push_button, sync_button]
    for btn in buttons:
        update_sts(btn.config, state=state)

def set_status(text):
    update_sts(status_var.set, value=text)

def add_placeholder(entry, placeholder):
    branch_var.set(placeholder)

# ======================================================================================================================
# INTERFACE
# ======================================================================================================================

root = tk.Tk()
root.title("QuikBash Alpha 1.8")
root.geometry("400x450")

style = ttk.Style()
style.theme_use('clam')

folder_var = tk.StringVar()
url_var = tk.StringVar()
branch_var = tk.StringVar()
msg_var = tk.StringVar()

folder_var.trace_add("write", validate_fields)
url_var.trace_add("write", validate_fields)
msg_var.trace_add("write", validate_fields)

tk.Label(root, text="Folder Path:", font=('Arial', 10, 'bold')).pack(pady=(10, 0))
folder_entry = ttk.Combobox(root, width=50, textvariable=folder_var)
folder_entry.pack(pady=5)
folder_entry['values'] = load_history()

tab_control = ttk.Notebook(root)
tab1 = ttk.Frame(tab_control)
tab2 = ttk.Frame(tab_control)
tab_control.add(tab1, text="New Repo")
tab_control.add(tab2, text="Update Repo")
tab_control.pack(expand=True, fill="both", padx=10, pady=10)

# TAB 1
# URL entry
tk.Label(tab1, text="GitHub URL:").pack(pady=(10, 0))
url_entry = tk.Entry(tab1, width=40, textvariable=url_var)
url_entry.pack(pady=5)

# Init Button
init_button = ttk.Button(tab1, text="Initialize & Push", command=lambda: run_async(init_new_repo), state="disabled")
init_button.pack(pady=20)

# TAB 2
# branch entry
tk.Label(tab2, text="Branch:").pack(pady=(10, 0))
branch_entry = tk.Entry(tab2, width=40, textvariable=branch_var)
branch_entry.pack(pady=5)
add_placeholder(branch_entry, "main")

# message entry
tk.Label(tab2, text="Commit Message:").pack(pady=(10, 0))
commit_entry = tk.Entry(tab2, width=40, textvariable=msg_var)
commit_entry.pack(pady=5)

# buttons
anc_button = ttk.Button(tab2, text="Add & Commit", command=lambda: run_async(commit_changes), state="disabled")
anc_button.pack(pady=(20, 5))
push_button = ttk.Button(tab2, text="Push to GitHub", command=lambda: run_async(push_to_github), state="disabled")
push_button.pack(pady=5)
sync_button = ttk.Button(tab2, text="Do All", command=lambda: run_async(do_all), state="disabled")
sync_button.pack(pady=5)

# STATUS
status_frame = tk.Frame(root, bd=1, relief=tk.SUNKEN)
status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
status_var = tk.StringVar(value="READY")
status_label = ttk.Label(status_frame, textvariable=status_var)
status_label.pack(fill=tk.X)

root.mainloop()