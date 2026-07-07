# GUI library
import tkinter as tk

# submodules: messagebox => pop-up windows, ttk => themed tk (modern look/widgets)
from tkinter import messagebox, ttk

# allow py to talk to file sys
import os

# allow py to run ext commands (git)
import subprocess


# --- Logic Functions ---

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


def init_new_repo():
    folder = folder_entry.get()
    url = url_entry.get()
    if not folder or not url:
        messagebox.showwarning("Input", "Please enter both folder path and GitHub URL!")
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
            messagebox.showerror("Git Error", f"Failed at: {' '.join(cmd)}\n{result.stderr}")
            return
    messagebox.showinfo("Success", "Repository initialized and pushed successfully!")


def commit_changes():
    folder = folder_entry.get()
    msg = commit_entry.get()

    if not msg:
        messagebox.showwarning("Input", "Please enter a commit message!")
        return

    if not validate_environment(folder): return

    status = subprocess.run(['git', '-C', folder, 'status', '--porcelain'], capture_output=True, text=True)
    if not status.stdout.strip():
        messagebox.showinfo("Status", "No changes detected.")
        return

    subprocess.run(['git', '-C', folder, 'add', '.'])
    result = subprocess.run(['git', '-C', folder, 'commit', '-m', msg], capture_output=True, text=True)

    if result.returncode == 0:
        messagebox.showinfo("Success", "Changes committed!")
    else:
        messagebox.showerror("Git Error", result.stderr)


def push_to_github():
    folder = folder_entry.get()
    if not validate_environment(folder): return

    status = subprocess.run(['git', '-C', folder, 'status', '--porcelain'], capture_output=True, text=True)
    if status.stdout.strip():
        messagebox.showerror("Push Blocked", "Uncommitted changes detected! Please commit them first.")
        return

    result = subprocess.run(['git', '-C', folder, 'push', '-u', 'origin', 'main'], capture_output=True, text=True)
    if result.returncode == 0:
        messagebox.showinfo("Success", "Pushed to GitHub!")
    else:
        messagebox.showerror("Push Failed", result.stderr)


# --- GUI Setup ---

root = tk.Tk()
root.title("QuikBash Alpha 1.0")
root.geometry("400x450")

tk.Label(root, text="Folder Path:", font=('Arial', 10, 'bold')).pack(pady=(10, 0))
folder_entry = tk.Entry(root, width=50)
folder_entry.pack(pady=5)

tab_control = ttk.Notebook(root)
tab1 = ttk.Frame(tab_control)
tab2 = ttk.Frame(tab_control)
tab_control.add(tab1, text="New Repo")
tab_control.add(tab2, text="Update Repo")
tab_control.pack(expand=True, fill="both", padx=10, pady=10)

# Tab 1
tk.Label(tab1, text="GitHub URL:").pack(pady=(10, 0))
url_entry = tk.Entry(tab1, width=40)
url_entry.pack(pady=5)
tk.Button(tab1, text="Initialize & Push", command=init_new_repo, bg="#e1e1e1").pack(pady=20)

# Tab 2
tk.Label(tab2, text="Commit Message:").pack(pady=(10, 0))
commit_entry = tk.Entry(tab2, width=40)
commit_entry.pack(pady=5)
tk.Button(tab2, text="Add & Commit", command=commit_changes).pack(pady=5)
tk.Button(tab2, text="Push to GitHub", command=push_to_github).pack(pady=5)

root.mainloop()