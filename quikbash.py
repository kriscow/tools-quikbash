import tkinter as tk
from tkinter import messagebox, ttk
import os
import subprocess

def validate_environment(folder_name, check_git=True):
    if not os.path.isdir(folder_name):
        messagebox.showerror("Error", f"The path '{folder_name}' is not a valid directory.")
        return False

    if check_git:
        # '-C' tells git to run in that folder
        result = subprocess.run(['git', '-C', folder_name, 'rev-parse', '--is-inside-work-tree'],
                                capture_output=True, text=True)
        if result.returncode != 0:
            messagebox.showerror("Error", "This folder is not a Git repository. Please initialize it first.")
            return False
    return True

def run_git_init():
    folder_name = folder_entry.get()
    if not folder_name:
        messagebox.showwarning("Input Error", "Please enter a folder name!")
        return

    if not os.path.exists(folder_name):
        os.makedirs(folder_name)  # makedirs is safer than mkdir

    result = subprocess.run(['git', '-C', folder_name, 'init'], capture_output=True, text=True)
    if result.returncode == 0:
        messagebox.showinfo("Success", "Git initialized successfully.")
    else:
        messagebox.showerror("Error", result.stderr)

def add_remote():
    folder_name = folder_entry.get()
    repo_url = remote_entry.get()

    if not validate_environment(folder_name, check_git=True): return
    if not repo_url:
        messagebox.showwarning("Input", "Please enter a GitHub URL.")
        return

    # Check if remote already exists
    check = subprocess.run(['git', '-C', folder_name, 'remote', 'get-url', 'origin'], capture_output=True)
    if check.returncode == 0:
        messagebox.showwarning("Info", "Remote 'origin' already exists.")
        return

    result = subprocess.run(['git', '-C', folder_name, 'remote', 'add', 'origin', repo_url], capture_output=True,
                            text=True)
    if result.returncode == 0:
        messagebox.showinfo("Success", "Remote added!")
    else:
        messagebox.showerror("Error", result.stderr)

def commit_changes():
    folder_name = folder_entry.get()

    # Check which tab is active and get the correct commit message
    current_tab = tab_control.index(tab_control.select())

    if current_tab == 0:  # Tab 1
        commit_msg = commit_entry.get()
    else:  # Tab 2
        commit_msg = commit_entry_tab2.get()

    if not commit_msg:
        messagebox.showwarning("Input", "Please enter a commit message!")
        return

    status_check = subprocess.run(['git', '-C', folder_name, 'status', '--porcelain'],
                                  capture_output=True, text=True)

    if not status_check.stdout.strip():
        messagebox.showinfo("Status", "No changes detected. Working tree is clean!")
        return

    subprocess.run(['git', '-C', folder_name, 'add', '.'])
    result = subprocess.run(['git', '-C', folder_name, 'commit', '-m', commit_msg], capture_output=True, text=True)

    if result.returncode == 0:
        messagebox.showinfo("Success", "Changes committed!")
    else:
        messagebox.showerror("Git Error", result.stderr)

def push_to_github():
    folder_name = folder_entry.get()
    if not validate_environment(folder_name, check_git=True): return

    # Check for uncommitted changes
    status_check = subprocess.run(['git', '-C', folder_name, 'status', '--porcelain'],
                                  capture_output=True, text=True)

    # If the output is NOT empty, we have files that aren't committed yet
    if status_check.stdout.strip():
        messagebox.showerror("Push Blocked", "You have uncommitted changes! Please commit them first.")
        return  # This STOPs the function here, so the push command never runs

    # If we get past that 'if', then it is safe to push
    subprocess.run(['git', '-C', folder_name, 'branch', '-M', 'main'])
    result = subprocess.run(['git', '-C', folder_name, 'push', '-u', 'origin', 'main'],
                            capture_output=True, text=True)

    if result.returncode == 0:
        messagebox.showinfo("Success", "Pushed to GitHub!")
    else:
        messagebox.showerror("Push Failed", result.stderr)

root = tk.Tk()
root.title("Git Quick-Clicker Pro")
root.geometry("400x500")

tk.Label(root, text="Enter Folder Path:", font=('Arial', 10, 'bold')).pack(pady=(10, 0))
folder_entry = tk.Entry(root, width=50)
folder_entry.pack(pady=5)

tab_control = ttk.Notebook(root)
tab1 = ttk.Frame(tab_control);
tab2 = ttk.Frame(tab_control)
tab_control.add(tab1, text="New Repository");
tab_control.add(tab2, text="Update Repository")
tab_control.pack(expand=1, fill="both", padx=10, pady=10)

# Tab 1 Layout
tk.Button(tab1, text="1. Initialize Git", command=run_git_init).pack(pady=5)
remote_entry = tk.Entry(tab1, width=40);
remote_entry.pack(pady=5)
tk.Button(tab1, text="2. Add Remote", command=add_remote).pack(pady=5)
commit_entry = tk.Entry(tab1, width=40);
commit_entry.pack(pady=5)
tk.Button(tab1, text="3. Add & Commit", command=commit_changes).pack(pady=5)
tk.Button(tab1, text="4. Push to GitHub", command=push_to_github).pack(pady=5)

# Tab 2 Layout
commit_entry_tab2 = tk.Entry(tab2, width=40);
commit_entry_tab2.pack(pady=5)
tk.Button(tab2, text="1. Add & Commit", command=commit_changes).pack(pady=10)
tk.Button(tab2, text="2. Push to GitHub", command=push_to_github).pack(pady=10)

root.mainloop()