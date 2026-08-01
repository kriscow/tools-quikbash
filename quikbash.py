import tkinter as tk  # GUI
from tkinter import messagebox, ttk  # GUI submodules
import os  # py <> file system communication
import subprocess  # py <> CLI communication
import threading  # freeze prevention

h_file = "qb_history.txt"
startup_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

# ======================================================================================================================
# VALIDATION ===========================================================================================================
# ======================================================================================================================

def validate_fields(*args):
    """Disable buttons if at least one required entry is empty."""
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

    if folder_var.get().strip():
        pull_button.config(state="normal")
    else:
        pull_button.config(state="disabled")

# ======================================================================================================================
def validate_environment(folder_name, check_git=True):
    """Verifies the existence of the target path (though optional) and confirms if it is Git-ready."""
    if not os.path.isdir(folder_name):
        messagebox.showerror("Error", f"Path '{folder_name}' is not a valid directory.")
        return False
    if check_git:
        result = subprocess.run(['git', '-C', folder_name, 'rev-parse', '--is-inside-work-tree'],
                                capture_output=True, text=True, creationflags=startup_flags)
        if result.returncode != 0:
            messagebox.showerror("Error", "Not a Git repository. Initialize it first.")
            return False
    return True

# ======================================================================================================================
# COMMANDS =============================================================================================================
# ======================================================================================================================

def init_new_repo():
    """Merge all Git initialization commands into one button."""
    folder = folder_entry.get().strip()
    url = url_entry.get().strip()

    update_btns("disabled")
    update_sts(init_button.config, text="Processing...")

    try:
        if not folder or not url:
            update_sts(messagebox.showwarning, title="Input", message="Please enter both folder path and GitHub URL!")
            return

        # Check if it's already a git repo
        is_git_repo = subprocess.run(['git', '-C', folder, 'rev-parse', '--is-inside-work-tree'],
                                     capture_output=True, text=True, creationflags=startup_flags)

        # Only run init if not a git repo
        if is_git_repo.returncode != 0:
            result = subprocess.run(['git', '-C', folder, 'init'], capture_output=True, text=True,
                                    creationflags=startup_flags)
            if result.returncode != 0:
                update_sts(messagebox.showerror, title="Git Error", message=f"Failed to init: {result.stderr}")
                return

        # Add all files
        result = subprocess.run(['git', '-C', folder, 'add', '.'], capture_output=True, text=True,
                                creationflags=startup_flags)
        if result.returncode != 0:
            update_sts(messagebox.showerror, title="Git Error", message=f"Failed to add: {result.stderr}")
            return

        # Check if there are changes to commit
        status = subprocess.run(['git', '-C', folder, 'status', '--porcelain'],
                                capture_output=True, text=True, creationflags=startup_flags)

        # Only commit if there are changes
        if status.stdout.strip():
            result = subprocess.run(['git', '-C', folder, 'commit', '-m', 'Initial commit'],
                                    capture_output=True, text=True, creationflags=startup_flags)
            if result.returncode != 0:
                update_sts(messagebox.showerror, title="Git Error", message=f"Failed at commit: {result.stderr}")
                return
        else:
            set_status("NO CHANGES TO COMMIT")

        # Set branch to main
        result = subprocess.run(['git', '-C', folder, 'branch', '-M', 'main'],
                                capture_output=True, text=True, creationflags=startup_flags)
        if result.returncode != 0:
            update_sts(messagebox.showerror, title="Git Error", message=f"Failed to set branch: {result.stderr}")
            return

        # Check if remote already exists
        remote_check = subprocess.run(['git', '-C', folder, 'remote', 'get-url', 'origin'],
                                      capture_output=True, text=True, creationflags=startup_flags)

        if remote_check.returncode != 0:
            # Add remote if it does not exist
            result = subprocess.run(['git', '-C', folder, 'remote', 'add', 'origin', url],
                                    capture_output=True, text=True, creationflags=startup_flags)
            if result.returncode != 0:
                update_sts(messagebox.showerror, title="Git Error", message=f"Failed to add remote: {result.stderr}")
                return
        else:
            # Update remote URL if it exists
            result = subprocess.run(['git', '-C', folder, 'remote', 'set-url', 'origin', url],
                                    capture_output=True, text=True, creationflags=startup_flags)
            if result.returncode != 0:
                update_sts(messagebox.showerror, title="Git Error", message=f"Failed to update remote: {result.stderr}")
                return

        # Check if remote has content (for fresh repo)
        set_status("CHECKING REMOTE...")
        remote_check = subprocess.run(['git', '-C', folder, 'ls-remote', 'origin', 'main'],
                                      capture_output=True, text=True, creationflags=startup_flags)

        # Only try to pull if remote has content
        if remote_check.stdout.strip():
            set_status("REMOTE HAS CONTENT - PULLING...")
            pull_result = subprocess.run(['git', '-C', folder, 'pull', 'origin', 'main', '--allow-unrelated-histories'],
                                         capture_output=True, text=True, creationflags=startup_flags)
            if pull_result.returncode != 0:
                update_sts(messagebox.showwarning, title="Pull Warning",
                           message=f"Pull had issues, trying to continue...\n{pull_result.stderr}")
        else:
            set_status("REMOTE IS EMPTY - READY TO PUSH")

        # Push to GitHub
        set_status("PUSHING TO GITHUB...")
        result = subprocess.run(['git', '-C', folder, 'push', '-u', 'origin', 'main'],
                                capture_output=True, text=True, creationflags=startup_flags)
        if result.returncode != 0:
            update_sts(messagebox.showerror, title="Git Error", message=f"Failed at push: {result.stderr}")
            return

        save_history(folder)
        set_status("CONNECTED TO GITHUB")

    finally:
        update_btns("normal")
        validate_fields()
        update_sts(init_button.config, text="Initialize & Push")

# ======================================================================================================================
def do_all():
    """Merge all Git repository update commands into one button."""
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

        # Do not commit if changes need to be pulled first
        set_status("PREPARING TO COMMIT...")
        fetch_result = subprocess.run(['git', '-C', folder, 'fetch', 'origin', branch], capture_output=True, text=True, creationflags=startup_flags)
        if fetch_result.returncode != 0: pass
        behind_check = subprocess.run(['git', '-C', folder, 'rev-list', '--count', f'HEAD..origin/{branch}'], capture_output=True, text=True, creationflags=startup_flags)

        if behind_check.stdout.strip() and int(behind_check.stdout.strip()) > 0:
            response = messagebox.askyesno(
                "Remote Has New Changes",
                "Remote has new commits that you don't have locally.\n\n"
                "Do you want to pull them first before committing?"
            )
            if response:
                pull_result = subprocess.run(['git', '-C', folder, 'pull', 'origin', branch], capture_output=True, text=True, creationflags=startup_flags)
                if pull_result.returncode != 0:
                    update_sts(messagebox.showerror, title="Pull Failed", message=f"Pull failed:\n{pull_result.stderr}")
                    return
                set_status("PULL COMPLETED")

        checkout_res = subprocess.run(['git', '-C', folder, 'checkout', branch],
                                      capture_output=True, text=True, creationflags=startup_flags)
        if checkout_res.returncode != 0:
            create_res = subprocess.run(['git', '-C', folder, 'checkout', '-b', branch],
                                        capture_output=True, text=True, creationflags=startup_flags)
            if create_res.returncode != 0:
                update_sts(messagebox.showerror, title="Git Error",
                           message=f"Could not create to branch '{branch}':\n{checkout_res.stderr}")
                return
            else:
                set_status(f"CREATED % SWITCHED TO BRANCH: {branch}")
        else:
            set_status(f"SWITCHED TO BRANCH: {branch}")

        status = subprocess.run(['git', '-C', folder, 'status', '--porcelain'],
                                capture_output=True, text=True, creationflags=startup_flags)
        if not status.stdout.strip():
            update_sts(messagebox.showinfo, title="Status", message="No changes detected.")
            return

        commands = [
            ['git', '-C', folder, 'add', '-A'],
            ['git', '-C', folder, 'commit', '-m', msg],
            ['git', '-C', folder, 'push', '-u', 'origin', branch]
        ]

        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=startup_flags)
            if result.returncode != 0:
                update_sts(messagebox.showerror, title="Git Error",
                           message=f"Failed at: {' '.join(cmd)}\n{result.stderr}")
                return

        save_history(folder)
        set_status("REPOSITORY UPDATED")

    finally:
        update_btns("normal")
        validate_fields()
        update_sts(sync_button.config, text="Do All")

# ======================================================================================================================
def commit_changes():
    """Merge 'Add all' and 'Commit' into one button."""
    folder = folder_entry.get().strip()
    msg = commit_entry.get().strip()

    update_btns("disabled")
    update_sts(anc_button.config, text="Processing...")

    try:
        if not msg:
            update_sts(messagebox.showwarning, title="Input", message="Please enter a commit message!")
            return

        if not validate_environment(folder): return

        status = subprocess.run(['git', '-C', folder, 'status', '--porcelain'],
                                capture_output=True, text=True, creationflags=startup_flags)

        if not status.stdout.strip():
            update_sts(messagebox.showinfo, title="Status", message="No changes detected.\n\nTip: Git doesn't track empty folders. Add a file to the folder first.")
            return

        subprocess.run(['git', '-C', folder, 'add', '-A'], creationflags=startup_flags)
        result = subprocess.run(['git', '-C', folder, 'commit', '-m', msg],
                                capture_output=True, text=True, creationflags=startup_flags)

        if result.returncode == 0:
            set_status("READY TO PUSH")
        else:
            update_sts(messagebox.showerror, title="Git Error", message=result.stderr)

    finally:
        update_btns("normal")
        validate_fields()
        update_sts(anc_button.config, text="Add & Commit")

# ======================================================================================================================
def push_to_github():
    """Finally push commitments to the connected GitHub repository."""
    folder = folder_entry.get().strip()
    branch = branch_var.get().strip()

    update_btns("disabled")
    update_sts(push_button.config, text="Processing...")

    try:
        if not validate_environment(folder): return

        if not branch:
            branch = "main"
            branch_var.set("main")

        # Do not push if changes need to be pulled first
        set_status("CHECKING REMOTE STATUS...")

        checkout_res = subprocess.run(['git', '-C', folder, 'checkout', branch],
                                      capture_output=True, text=True, creationflags=startup_flags)
        if checkout_res.returncode != 0:
            create_res = subprocess.run(['git', '-C', folder, 'checkout', '-b', branch],
                                        capture_output=True, text=True, creationflags=startup_flags)
            if create_res.returncode != 0:
                update_sts(messagebox.showerror, title="Git Error",
                           message=f"Could not create to branch '{branch}':\n{checkout_res.stderr}")
                return
            else:
                set_status(f"CREATED % SWITCHED TO BRANCH: {branch}")
        else:
            set_status(f"SWITCHED TO BRANCH: {branch}")

        # Do not push if changes are uncommitted
        status = subprocess.run(['git', '-C', folder, 'status', '--porcelain'],
                                capture_output=True, text=True, creationflags=startup_flags)
        if status.stdout.strip():
            update_sts(messagebox.showerror, title="Push Blocked",
                       message="Uncommitted changes detected! Please commit them first.")
            return

        # Do not push if version is up to date
        check_push = subprocess.run(['git', '-C', folder, 'log', f'origin/{branch}..{branch}', '--oneline'],
                                    capture_output=True, text=True, creationflags=startup_flags)
        if not check_push.stdout.strip():
            update_sts(messagebox.showinfo, title="Push Status", message="Everything is already up to date!")
            return

        # Push if previous checks are not met
        set_status("PUSHING TO GITHUB...")
        result = subprocess.run(['git', '-C', folder, 'push', '-u', 'origin', branch], capture_output=True, text=True, creationflags=startup_flags)

        if result.returncode == 0:
            save_history(folder)
            set_status("REPOSITORY UPDATED")
        else:
            if "rejected" in result.stderr.lower() and "fetch first" in result.stderr.lower():
                update_sts(messagebox.showerror, title="Push Failed",
                           message="Remote has new commits!\n\nClick 'Pull Latest' first to get them, then try pushing again.")
            else:
                update_sts(messagebox.showerror, title="Push Failed", message=result.stderr)

    finally:
        update_btns("normal")
        validate_fields()
        update_sts(push_button.config, text="Push to GitHub")

# ======================================================================================================================
def pull_from_github():
    """Pull to get latest changes from remote."""
    folder = folder_entry.get().strip()
    branch = branch_var.get().strip() or "main"

    update_btns("disabled")
    update_sts(pull_button.config, text="Pulling...")

    try:
        if not folder:
            update_sts(messagebox.showwarning, title="Input", message="Please enter a folder path!")
            return

        if not validate_environment(folder): return

        set_status(f"PULLING FROM {branch}...")
        result = subprocess.run(['git', '-C', folder, 'pull', 'origin', branch],
                                capture_output=True, text=True, creationflags=startup_flags)

        if result.returncode == 0:
            save_history(folder)
            set_status("PULL SUCCESSFUL")
            messagebox.showinfo("Success", f"Latest changes pulled successfully from '{branch}'!")
        else:
            if "no such remote" in result.stderr.lower():
                update_sts(messagebox.showerror, title="Pull Failed",
                           message="No remote 'origin' found. Initialize the repo first with 'New Repo' tab.")
            else:
                update_sts(messagebox.showerror, title="Pull Failed",
                           message=f"Pull failed:\n{result.stderr}")

    finally:
        update_btns("normal")
        validate_fields()
        update_sts(pull_button.config, text="Pull Latest")

# ======================================================================================================================
# HISTORY ==============================================================================================================
# ======================================================================================================================

def load_history():
    """Load the (5) most recently initialized/updated repositories."""
    if os.path.exists(h_file):
        try:
            with open(h_file, 'r') as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        except Exception:
            return []
    return []

# ======================================================================================================================
def save_history(path):
    """If path is new, save it."""
    history = load_history()

    if path in history:
        history.remove(path)
    history.insert(0, path)
    history = history[:5]

    with open(h_file, 'w') as f:
        f.write('\n'.join(history))
    folder_entry['values'] = history

# ======================================================================================================================
# HELPERS ==============================================================================================================
# ======================================================================================================================

# Threading
def run_async(func):
    threading.Thread(target=func, daemon=True).start()

# Process State (messagebox & button text)
def update_sts(func, **kwargs):
    root.after(0, lambda: func(**kwargs))

# Button State (en/disabled)
def update_btns(state):
    buttons = [init_button, anc_button, push_button, sync_button, pull_button]
    for btn in buttons:
        update_sts(btn.config, state=state)

# Status Text
def set_status(text):
    update_sts(status_var.set, value=text)

# Branch Entry Placeholder
def add_placeholder(entry, placeholder):
    branch_var.set(placeholder)

# ======================================================================================================================
# INTERFACE ============================================================================================================
# ======================================================================================================================

# Base
root = tk.Tk()
root.title("QuikBash Beta 1.5")
root.geometry("425x425")

# Theme
style = ttk.Style()
style.theme_use('clam')

# Palette
orange = "#FF7F11"
dark = "#262626"
white = "#FFFFFF"
green = "#2F6B3F"

# Base Style
root.configure(background=white)
style.configure(".", background=white, foreground=dark, fieldbackground=white)

# Buttons
style.configure("TButton", background=dark, foreground=white, borderwidth=0, padding=6)
style.map("TButton", background=[("active", orange), ("disabled", "#D0D0D0")], foreground=[("active", white), ("disabled", "#888888")])

# Tabs
style.configure("TNotebook", background=white, borderwidth=0)
style.configure("TNotebook.Tab", background="#F0F0F0", foreground=dark, padding=[20, 8])
style.map("TNotebook.Tab", background=[("selected", orange)], foreground=[("selected", white)], padding=[("selected", [20, 8])])

# Entries, Comboboxes
style.configure("TEntry", fieldbackground=white, bordercolor=dark, lightcolor=dark)
style.configure("TCombobox", fieldbackground=white, bordercolor=dark)
style.map("TEntry", fieldbackground=[("focus", white)], selectbackground=[("!disabled", dark)], selectforeground=[("!disabled", white)])
style.map("TCombobox", fieldbackground=[("focus", white)], selectbackground=[("!disabled", dark)], selectforeground=[("!disabled", white)])

# Status Text
style.configure("Status.TLabel", background=white, foreground=dark, padding=10)

# Entry Vars
folder_var = tk.StringVar()
url_var = tk.StringVar()
branch_var = tk.StringVar()
msg_var = tk.StringVar()

# Smart Enabling (see validate_fields)
folder_var.trace_add("write", validate_fields)
url_var.trace_add("write", validate_fields)
msg_var.trace_add("write", validate_fields)

# Folder Path UI
ttk.Label(root, text="Folder Path:", font=('Arial', 10, 'bold')).pack(pady=(20, 0))
folder_entry = ttk.Combobox(root, width=50, textvariable=folder_var)
folder_entry.pack(pady=(5, 30), padx=20, fill=tk.X)
folder_entry['values'] = load_history()

# Tab Control
tab_control = ttk.Notebook(root)
tab1 = ttk.Frame(tab_control, padding=10)
tab2 = ttk.Frame(tab_control, padding=10)
tab_control.add(tab1, text="New Repository")
tab_control.add(tab2, text="Update Repository")
tab_control.pack(expand=True, fill="both", padx=10)

# Tab 1 (New Repo)
ttk.Label(tab1, text="Remote URL:").pack(pady=(10, 0))
url_entry = ttk.Entry(tab1, textvariable=url_var)
url_entry.pack(pady=5, fill=tk.X)

init_button = ttk.Button(tab1, text="INIT & PUSH", command=lambda: run_async(init_new_repo), state="disabled")
init_button.pack(fill=tk.X, pady=5)

# Tab 2 (Update Repo)
ttk.Label(tab2, text="Branch:").pack(pady=(10, 0))
branch_entry = ttk.Entry(tab2, textvariable=branch_var)
branch_entry.pack(pady=5, fill=tk.X)
add_placeholder(branch_entry, "main")

ttk.Label(tab2, text="Message:").pack(pady=(10, 0))
commit_entry = ttk.Entry(tab2, textvariable=msg_var)
commit_entry.pack(pady=5, fill=tk.X)

button_frame = ttk.Frame(tab2)
button_frame.pack(pady=(20, 10), fill=tk.X)
button_frame.columnconfigure(0, weight=1)
button_frame.columnconfigure(1, weight=1)

anc_button = ttk.Button(button_frame, text="COMMIT", command=lambda: run_async(commit_changes), state="disabled")
anc_button.grid(row=0, column=0, padx=(0, 5), pady=(0, 5), sticky="ew")

push_button = ttk.Button(button_frame, text="PUSH", command=lambda: run_async(push_to_github), state="disabled")
push_button.grid(row=0, column=1, padx=(5, 0), pady=(0, 5), sticky="ew")

sync_button = ttk.Button(button_frame, text="COMMIT & PUSH", command=lambda: run_async(do_all), state="disabled")
sync_button.grid(row=1, column=0, padx=(0, 5), pady=(5, 0), sticky="ew")

pull_button = ttk.Button(button_frame, text="PULL", command=lambda: run_async(pull_from_github), state="disabled")
pull_button.grid(row=1, column=1, padx=(5, 0), pady=(5, 0), sticky="ew")

# Status Text
status_frame = ttk.Frame(root)
status_frame.pack(side=tk.BOTTOM, fill=tk.X)
status_var = tk.StringVar(value="READY")
status_label = ttk.Label(status_frame, textvariable=status_var, style="Status.TLabel", anchor="center", font=('Arial', 9, 'bold'))
status_label.pack(fill=tk.X, padx=10, pady=(0, 3))

root.mainloop()