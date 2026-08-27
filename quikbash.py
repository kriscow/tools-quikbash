import os
import time
import threading
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

# Global Variables
startup_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
h_file = "qb_history.txt"
b_file = "qb_branches.txt"
MAX_HISTORY = 5
MAX_BRANCHES = 64

# Palette
orange = "#FF7F11"
dark = "#262626"
white = "#FFFFFF"
green = "#2F6B3F"

# STATE MANAGEMENT #####################################################################################################

class AppState:
    def __init__(self):
        self.history = []
        self.branches = []
        self.load_history()
        self.load_branches()
        self.is_processing = False

    def load_history(self):
        """Load saved repo path"""
        if os.path.exists(h_file):
            try:
                with open(h_file, 'r') as f:
                    self.history = [line.strip() for line in f.readlines() if line.strip()]
            except Exception:
                self.history = []
        return self.history

    def save_history(self, path):
        """Save a new repo path"""
        if path in self.history:
            self.history.remove(path)
        self.history.insert(0, path)
        self.history = self.history[:MAX_HISTORY]
        with open(h_file, 'w') as f:
            f.write('\n'.join(self.history))

    def is_in_history(self, path):
        """Check if path exists in history"""
        return path in self.history

    def load_branches(self):
        """Load existing branches"""
        if os.path.exists(b_file):
            try:
                with open(b_file, 'r') as f:
                    self.branches = [line.strip() for line in f.readlines() if line.strip()]
            except Exception:
                self.branches = []
        return self.branches

    def save_branches(self, branch):
        """Save new branches"""
        if not branch or branch == "main": return
        if branch in self.branches:
            self.branches.remove(branch)
        self.branches.insert(0, branch)
        self.branches = self.branches[:MAX_BRANCHES]
        with open(b_file, 'w') as f:
            f.write('\n'.join(self.branches))

    def is_in_branches(self, branch):
        """Check if branch exists in repository"""
        return branch in self.branches

app_state = AppState()

# VALIDATION ###########################################################################################################

def validate_fields(*args):
    """Enable/disable buttons"""
    # For init / re-link
    if folder_var.get().strip() and url_var.get().strip():
        init_button.config(state="normal")
    else:
        init_button.config(state="disabled")
    update_init_button_label()

    # For git commands
    can_operate = bool(folder_var.get().strip() and msg_var.get().strip())
    for btn in [anc_button, push_button, sync_button]:
        if can_operate:
            btn.config(state="normal")
        else:
            btn.config(state="disabled")

    # For git (pull) command
    folder = folder_var.get().strip()
    if folder:
        pull_button.config(state="normal")
        if os.path.isdir(folder) and os.path.exists(os.path.join(folder, '.git')): # If folder is a valid git repo, fetch branches
            branches = fetch_branches_from_repo(folder)
            if branches:
                # Merge with saved history
                all_branches = list(set(branches + app_state.branches))
                all_branches.sort()
                # Keep 'main' at the top
                if 'main' in all_branches:
                    all_branches.remove('main')
                    all_branches.insert(0, 'main')
                branch_entry['values'] = all_branches
    else: # Restore saved history if no folder
        pull_button.config(state="disabled")
        branch_entry['values'] = app_state.branches

def validate_environment(folder_name, check_git=True):
    """Folder exists && Git repo"""
    if not os.path.isdir(folder_name):
        messagebox.showerror("Error", f"Path '{folder_name}' is not a valid directory.")
        return False

    if check_git:
        result = subprocess.run(
            ['git', '-C', folder_name, 'rev-parse', '--is-inside-work-tree'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if result.returncode != 0:
            messagebox.showerror("Error", "Not a Git repository. Link it first.")
            return False
    return True

def update_init_button_label():
    """Update init / re-link button label (history-based)"""
    folder = folder_var.get().strip()
    if folder and app_state.is_in_history(folder): init_button.config(text="RE-LINK")
    else: init_button.config(text="LINK")

# HELPERS ##############################################################################################################

def run_async(func):
    threading.Thread(target=func, daemon=True).start()

def update_sts(func, **kwargs):
    root.after(0, lambda: func(**kwargs))

def update_btns(state):
    buttons = [init_button, anc_button, push_button, sync_button, pull_button]
    for btn in buttons:
        update_sts(btn.config, state=state)

def set_status(text):
    update_sts(status_var.set, value=text)

def set_processing(active, status_txt="PROCESSING"):
    app_state.is_processing = active
    if active:
        update_btns("disabled")
        anim_status(status_txt)
    else:
        update_btns("normal")
        set_status("READY")
        validate_fields()

def anim_status(base, dot_count=0):
    if not app_state.is_processing: return
    dots = [".", "..", "..."]
    idx = dot_count % len(dots)
    set_status(f"{base}{dots[idx]}")
    root.after(500, lambda: anim_status(base, dot_count + 1))

def start_timer():
    return time.perf_counter()

def end_timer(start_time):
    elapsed = time.perf_counter() - start_time
    if elapsed < 1: return f"{elapsed*1000:.0f}ms"
    else: return f"{elapsed:.2f}s"

# COMMANDS #############################################################################################################

def init_new_repo():
    """Link / Re-Link > Push"""
    folder = folder_var.get().strip()
    url = url_var.get().strip()
    branch = "main"

    if not folder or not url:
        messagebox.showwarning("Input", "Please fill up all required fields.")
        return

    set_processing(True, status_txt="INITIALIZING")
    timer_start = start_timer()

    try:
        # 1.1) Check if has valid local
        is_git = subprocess.run(
            ['git', '-C', folder, 'rev-parse', '--is-inside-work-tree'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        # 1.2) If local exists, skip and proceed. Otherwise:
        if is_git.returncode != 0:
            result = subprocess.run(
                ['git', '-C', folder, 'init'],
                capture_output=True, text=True, creationflags=startup_flags
            )
            if result.returncode != 0:
                messagebox.showerror("Git Error", f"Failed to link: {result.stderr}")
                return

        # 2) Add all files
        result = subprocess.run(
            ['git', '-C', folder, 'add', '.'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if result.returncode != 0:
            messagebox.showerror("Git Error", f"Failed to add: {result.stderr}")
            return

        # 3.1) Check for uncommitted changes
        status = subprocess.run(
            ['git', '-C', folder, 'status', '--porcelain'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if status.stdout.strip(): # 3.2) If has uncommitted changes
            result = subprocess.run(
                ['git', '-C', folder, 'commit', '-m', 'Initial commit'],
                capture_output=True, text=True, creationflags=startup_flags
            )
            if result.returncode != 0:
                messagebox.showerror("Git Error", f"Failed at commit: {result.stderr}")
                return
        else:
            set_status("NO CHANGES TO COMMIT")

        # 4) Set branch to main (default)
        result = subprocess.run(
            ['git', '-C', folder, 'branch', '-M', 'main'], # Auto-renames branch to 'main'
            capture_output=True, text=True, creationflags=startup_flags
        )
        if result.returncode != 0:
            messagebox.showerror("Git Error", f"Failed to set branch: {result.stderr}")
            return

        # 5.1) Check if has valid remote
        remote_check = subprocess.run(
            ['git', '-C', folder, 'remote', 'get-url', 'origin'], # Check remote 'origin'
            capture_output=True, text=True, creationflags=startup_flags
        )
        if remote_check.returncode != 0: # 5.2) If no remote
            result = subprocess.run(
                ['git', '-C', folder, 'remote', 'add', 'origin', url],
                capture_output=True, text=True, creationflags=startup_flags
            )
            if result.returncode != 0:
                messagebox.showerror("Git Error", f"Failed to add remote: {result.stderr}")
                return
        else:
            result = subprocess.run(
                ['git', '-C', folder, 'remote', 'set-url', 'origin', url],
                capture_output=True, text=True, creationflags=startup_flags
            )
            if result.returncode != 0:
                messagebox.showerror("Git Error", f"Failed to update remote: {result.stderr}")
                return

        # 5.3) Check remote content
        set_status("CHECKING REMOTE...")
        remote_check = subprocess.run(
            ['git', '-C', folder, 'ls-remote', 'origin', 'main'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if remote_check.stdout.strip(): # 5.4) Pull if remote has content
            set_status("REMOTE HAS CONTENT > PULLING...")
            pull_result = subprocess.run(
                ['git', '-C', folder, 'pull', 'origin', 'main', '--allow-unrelated-histories'],
                capture_output=True, text=True, creationflags=startup_flags
            )
            if pull_result.returncode != 0:
                messagebox.showwarning("Pull Warning", f"Pull had issues:\n{pull_result.stderr}")
        else:
            set_status("REMOTE EMPTY > PUSHING...")

        # 6) Push
        set_status("PUSHING...")
        result = subprocess.run(
            ['git', '-C', folder, 'push', '-u', 'origin', 'main'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if result.returncode != 0:
            messagebox.showerror("Git Error", f"Failed at push: {result.stderr}")
            return

        app_state.save_history(folder)
        app_state.save_branches(branch)
        elapsed = end_timer(timer_start)
        set_status("INITIALIZE SUCCESS")
        messagebox.showinfo("Success", f"Initialization finished!\n\nProcess finished in {elapsed}.")
        branches = fetch_branches_from_repo(folder)
        if branches:
            all_branches = list(set(branches + app_state.branches))
            all_branches.sort()
            if 'main' in all_branches:
                all_branches.remove('main')
                all_branches.insert(0, 'main')
            branch_entry['values'] = all_branches
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        set_processing(False)

def do_all():
    """Add > Commit > Push"""
    folder = folder_var.get().strip()
    branch = branch_var.get().strip() or "main"
    msg = msg_var.get().strip()

    if not folder or not msg:
        messagebox.showwarning("Input", "Please fill up all entry fields.")
        return

    set_processing(True, status_txt="CHECKING UNPUSHED COMMITS")
    timer_start = start_timer()

    try:
        # 1) Check unpushed commits
        check_push = subprocess.run(
            ['git', '-C', folder, 'log', f'origin/{branch}..{branch}', '--oneline'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        has_unpushed = bool(check_push.stdout.strip())

        if has_unpushed:
            push_to_github(silent=True)
            app_state.save_branches(branch)
            elapsed = end_timer(timer_start)
            set_status("Found unpushed commits - pushing...")
            messagebox.showinfo("Success", f"Commits have been pushed!\n\nProcess finished in {elapsed}.")
            return

        # 2.1) Check uncommitted changes
        status = subprocess.run(
            ['git', '-C', folder, 'status', '--porcelain'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if status.stdout.strip(): # 2.2) If has uncommitted changes
            commit_changes(silent=True)
            push_to_github(silent=True)
            app_state.save_branches(branch)
            elapsed = end_timer(timer_start)
            set_status("PUSHING...")
            messagebox.showinfo("Success", f"Changes have been committed and pushed!\n\nProcess finished in {elapsed}.")
        else:
            set_status("EVERYTHING IS UP TO DATE")
            messagebox.showinfo("Status", "No changes detected.")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        set_processing(False)

def commit_changes(silent=False):
    """Add > Commit"""
    folder = folder_var.get().strip()
    msg = msg_var.get().strip()

    if not msg:
        messagebox.showwarning("Input", "Please enter a commit message.")
        return
    if not validate_environment(folder):
        return

    timer_start = start_timer()

    try:
        # 1.1) Check for content changes
        status = subprocess.run(
            ['git', '-C', folder, 'status', '--porcelain'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if not status.stdout.strip(): # 1.2) If no content changes
            if not silent:
                messagebox.showinfo("Status", "No changes to commit.")
            set_status("NO CHANGES")
            return

        # 2) If has content changes
        set_status("STAGING & COMMITTING...")
        subprocess.run(['git', '-C', folder, 'add', '-A'], creationflags=startup_flags)
        result = subprocess.run(
            ['git', '-C', folder, 'commit', '-m', msg],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if result.returncode == 0:
            app_state.save_history(folder)
            set_status("READY TO PUSH")
            if not silent:
                elapsed = end_timer(timer_start)
                messagebox.showinfo("Success", f"Changes have been committed!\n\nProcess finished in {elapsed}.")
        else:
            if not silent:
                elapsed = end_timer(timer_start)
                messagebox.showerror("Git Error", result.stderr)
    except Exception as e:
        if not silent:
            elapsed = end_timer(timer_start)
            messagebox.showerror("Error", str(e))

def push_to_github(silent=False):
    """Push"""
    folder = folder_var.get().strip()
    branch = branch_var.get().strip() or "main"

    if not validate_environment(folder): return
    timer_start = start_timer()

    try:
        # 1.1) Check if has local branch
        local_branch_check = subprocess.run(
            ['git', '-C', folder, 'rev-parse', '--verify', branch],
            capture_output=True, text=True, creationflags=startup_flags
        )
        local_branch = (local_branch_check.returncode == 0)

        if not local_branch:
            if not silent:
                set_status(f"CREATING BRANCH: {branch}")
            create_res = subprocess.run(
                ['git', '-C', folder, 'checkout', '-b', branch],
                capture_output=True, text=True, creationflags=startup_flags
            )
            if create_res.returncode != 0:
                if not silent:
                    messagebox.showerror("Git Error", f"Could not create branch '{branch}':\n{create_res.stderr}")
                return
            if not silent:
                set_status(f"CREATED BRANCH: {branch}")

        # 2.1) Switch to branch
        checkout_res = subprocess.run(
            ['git', '-C', folder, 'checkout', branch],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if checkout_res.returncode != 0:
            create_res = subprocess.run(
                ['git', '-C', folder, 'checkout', '-b', branch],
                capture_output=True, text=True, creationflags=startup_flags
            )
            if create_res.returncode != 0:
                if not silent:
                    messagebox.showerror("Git Error", f"Could not switch to branch '{branch}':\n{checkout_res.stderr}")
                return
            else:
                if not silent:
                    set_status(f"CREATED & SWITCHED TO BRANCH: {branch}")
        else:
            if not silent:
                set_status(f"SWITCHED TO BRANCH: {branch}")

        # 3.1) Check for uncommitted changes
        status = subprocess.run(
            ['git', '-C', folder, 'status', '--porcelain'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if status.stdout.strip():
            if not silent:
                elapsed = end_timer(timer_start)
                messagebox.showerror("Push Blocked", f"Uncommitted changes detected! Please commit them first.\n\nProcess finished in {elapsed}.")
            return

        # 4.1) Check if remote branch exists
        remote_branch_check = subprocess.run(
            ['git', '-C', folder, 'ls-remote', 'origin', branch],
            capture_output=True, text=True, creationflags=startup_flags
        )
        remote_branch_exists = bool(remote_branch_check.stdout.strip())

        # 4.2) If remote exists, check if there's anything to push
        if remote_branch_exists:
            check_push = subprocess.run(
                ['git', '-C', folder, 'log', f'origin/{branch}..{branch}', '--oneline'],
                capture_output=True, text=True, creationflags=startup_flags
            )
            if not check_push.stdout.strip():
                if not silent:
                    set_status("EVERYTHING UP TO DATE")
                    messagebox.showinfo("Push Status", "Everything is already up to date!")
                return
        else:
            if not silent: set_status(f"NEW REMOTE BRANCH: {branch}")

        # 5) Push
        if not silent: set_status("PUSHING...")

        result = subprocess.run(
            ['git', '-C', folder, 'push', '-u', 'origin', branch],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if result.returncode == 0:
            app_state.save_history(folder)
            app_state.save_branches(branch)
            if not silent:
                elapsed = end_timer(timer_start)
                set_status("REPOSITORY UPDATED")
                messagebox.showinfo("Success", f"Commits have been pushed!\n\nProcess finished in {elapsed}.")
        else:
            if "rejected" in result.stderr.lower():
                if not silent:
                    set_status("PUSH REJECTED > NEED TO PULL")
                    messagebox.showerror("Push Failed", "Remote has new commits!\n\nClick 'PULL' first, then try pushing again.")
            else:
                if not silent:
                    set_status("PUSH FAILED")
                    messagebox.showerror("Push Failed", result.stderr)
    except Exception as e:
        if not silent:
            messagebox.showerror("Error", str(e))

def pull_from_github():
    """Pull"""
    folder = folder_var.get().strip()
    branch = branch_var.get().strip() or "main"

    if not folder:
        messagebox.showwarning("Input", "Please enter a folder path.")
        return
    if not validate_environment(folder):
        return

    status = subprocess.run(
        ['git', '-C', folder, 'status', '--porcelain'],
        capture_output=True, text=True, creationflags=startup_flags)
    if status.stdout.strip():
        confirm = messagebox.askyesno(
            "Uncommitted Changes Detected",
            "You have uncommitted changes.\n"
            "Pulling may cause conflicts.\n\n"
            "Continue anyway?"
        )
        if not confirm:
            set_status("PULL CANCELLED")
            return
    else:
        confirm = messagebox.askyesno(
            "Confirmation",
            f"Pull latest from {branch}?\n\n"
            "This will download and merge changes from the remote.\n")

        if not confirm:
            set_status("PULL CANCELLED")
            return

    set_processing(True, status_txt=f"PULLING FROM {branch}")
    timer_start = start_timer()

    try:
        # 1.1) Check if can pull
        result = subprocess.run(
            ['git', '-C', folder, 'pull', 'origin', branch],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if result.returncode == 0: # 1.2) Success
            app_state.save_history(folder)
            elapsed = end_timer(timer_start)
            set_status("PULL SUCCESSFUL")
            messagebox.showinfo("Success", f"Latest changes pulled from '{branch}'!\n\nProcess finished in {elapsed}.")
            branches = fetch_branches_from_repo(folder)

            if branches:
                all_branches = list(set(branches + app_state.branches))
                all_branches.sort()
                if 'main' in all_branches:
                    all_branches.remove('main')
                    all_branches.insert(0, 'main')
                branch_entry['values'] = all_branches
        else:
            if "no such remote" in result.stderr.lower():
                set_status("NO REMOTE FOUND")
                messagebox.showerror("Pull Failed", "No remote 'origin' found. Link the repo first.")
            else:
                set_status("PULL FAILED")
                messagebox.showerror("Pull Failed", result.stderr)
    except Exception as e:
        elapsed = end_timer(timer_start)
        messagebox.showerror("Error", str(e))
    finally:
        set_processing(False)

def set_folder(path):
    """Set folder from history chip"""
    if path and path.strip():
        folder_var.set(path)
        app_state.save_history(path)
        validate_fields()

# OTHER ################################################################################################################

def fetch_branches_from_repo(folder):
    """Get all existing branches"""
    try:
        # Get local branches
        local_result = subprocess.run(
            ['git', '-C', folder, 'branch', '--format=%(refname:short)'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        local_branches = [b.strip() for b in local_result.stdout.splitlines() if b.strip()]

        # Get remote branches
        remote_result = subprocess.run(
            ['git', '-C', folder, 'branch', '-r', '--format=%(refname:short)'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        remote_branches = [b.strip().replace('origin/', '') for b in remote_result.stdout.splitlines() if b.strip()]

        # Combine
        all_branches = list(set(local_branches + remote_branches))
        all_branches = [b for b in all_branches if b != 'HEAD' and not b.endswith('HEAD')]
        all_branches.sort()
        return all_branches
    except Exception: return []

# INTERFACE ############################################################################################################

# Base
root = tk.Tk()
root.title("QuikBash")
root.geometry("425x425")
root.configure(background=white)

# Style
style = ttk.Style()
style.theme_use('clam')

# Base Style
style.configure(".", background=white, foreground=dark, fieldbackground=white)

# Buttons
style.configure("TButton", background=dark, foreground=white, borderwidth=0, padding=6)
style.map("TButton",
          background=[("active", orange), ("disabled", "#D0D0D0")],
          foreground=[("active", white), ("disabled", "#888888")])
# Tabs
style.configure("TNotebook", background=white, borderwidth=0)
style.configure("TNotebook.Tab", background="#F0F0F0", foreground=dark, padding=[20, 8])
style.map("TNotebook.Tab",
          background=[("selected", orange)],
          foreground=[("selected", white)],
          padding=[("selected", [20, 8])])
# Entries
style.configure("TEntry", fieldbackground=white, bordercolor=dark, lightcolor=dark)
style.configure("TCombobox", fieldbackground=white, bordercolor=dark)
style.map("TEntry",
          fieldbackground=[("focus", white)],
          selectbackground=[("!disabled", dark)],
          selectforeground=[("!disabled", white)])
style.map("TCombobox",
          fieldbackground=[("focus", white)],
          selectbackground=[("!disabled", dark)],
          selectforeground=[("!disabled", white)])
# Status Text
style.configure("Status.TLabel", background=white, foreground=dark, padding=10)

# Entry Vars
folder_var = tk.StringVar()
url_var = tk.StringVar()
branch_var = tk.StringVar()
msg_var = tk.StringVar()

# Button State
folder_var.trace_add("write", validate_fields)
url_var.trace_add("write", validate_fields)
msg_var.trace_add("write", validate_fields)

# Folder Path
ttk.Label(root, text="Folder Path:", font=('Arial', 10, 'bold')).pack(pady=(20, 0))
folder_entry = ttk.Combobox(root, width=50, textvariable=folder_var)
folder_entry.pack(pady=(5, 30), padx=20, fill=tk.X)
folder_entry['values'] = app_state.history

# Tab Setup
tab_control = ttk.Notebook(root)
tab1 = ttk.Frame(tab_control, padding=10)
tab2 = ttk.Frame(tab_control, padding=10)
tab_control.add(tab1, text="SETUP")
tab_control.add(tab2, text="WORK")
tab_control.pack(expand=True, fill="both", padx=10)

# Tab 1 (New Repo)
ttk.Label(tab1, text="Remote URL:").pack(pady=(10, 0))
url_entry = ttk.Entry(tab1, textvariable=url_var)
url_entry.pack(pady=5, fill=tk.X)

init_button = ttk.Button(tab1, text="LINK", command=lambda: run_async(init_new_repo), state="disabled")
init_button.pack(fill=tk.X, pady=5)

# Tab 2 (Update Repo)
ttk.Label(tab2, text="Branch:").pack(pady=(10, 0))
branch_entry = ttk.Combobox(tab2, width=50, textvariable=branch_var)
branch_entry.pack(pady=5, fill=tk.X)
branch_entry['values'] = app_state.branches
branch_var.set("main")

ttk.Label(tab2, text="Message:").pack(pady=(10, 0))
commit_entry = ttk.Entry(tab2, textvariable=msg_var)
commit_entry.pack(pady=5, fill=tk.X)

button_frame = ttk.Frame(tab2)
button_frame.pack(pady=(20, 10), fill=tk.X)
button_frame.columnconfigure(0, weight=1, uniform="a")
button_frame.columnconfigure(1, weight=1, uniform="a")

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

validate_fields()
root.mainloop()