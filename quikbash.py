import os
import time
import threading
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

# Global Variables
startup_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
h_file = "qb_history.txt"
MAX_HISTORY = 5

# Palette
orange = "#FF7F11"
dark = "#262626"
white = "#FFFFFF"
green = "#2F6B3F"

# STATE MANAGEMENT #####################################################################################################

class AppState:
    def __init__(self):
        self.history = []
        self.load_history()
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
        if os.path.isdir(folder) and os.path.exists(os.path.join(folder, '.git')): # If folder is a valid, fetch branches
            branches = fetch_branches_from_repo(folder)
            if branches:
                # Merge with saved history
                all_branches = branches
                all_branches.sort()
                # Keep 'main' at the top
                if 'main' in all_branches:
                    all_branches.remove('main')
                    all_branches.insert(0, 'main')
                branch_entry['values'] = all_branches
                merge_from_entry['values'] = all_branches
                merge_to_entry['values'] = all_branches
    else: # Blank if no folder
        pull_button.config(state="disabled")
        branch_entry['values'] = []
        merge_from_entry['values'] = []
        merge_to_entry['values'] = []

    # For git (branch) commands
    # Create button
    if branch_name_var.get().strip():
        create_button.config(state="normal")
    else:
        create_button.config(state="disabled")

    # Delete button
    if branch_name_var.get().strip() and branch_name_var.get().strip() != "main":
        delete_button.config(state="normal")
    else:
        delete_button.config(state="disabled")

    # Merge button
    if merge_from_var.get().strip() and merge_to_var.get().strip():
        merge_button.config(state="normal")
    else:
        merge_button.config(state="disabled")

def validate_environment(folder_name, check_git=True):
    """Folder exists && Git repo"""
    if not os.path.isdir(folder_name):
        messagebox.showerror("Error",
                             f"Path '{folder_name}' is not a valid directory.")
        return False

    if check_git:
        result = subprocess.run(
            ['git', '-C', folder_name, 'rev-parse', '--is-inside-work-tree'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if result.returncode != 0:
            messagebox.showerror("Error",
                                 "Not a Git repository. Link it first.")
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

# CORE COMMANDS ########################################################################################################

def init_new_repo():
    """Link / Re-Link > Push"""
    folder = folder_var.get().strip()
    url = url_var.get().strip()
    branch = "main"

    if not folder or not url:
        messagebox.showwarning("Input",
                               "Please fill up all required fields.")
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
                messagebox.showerror("Git Error",
                                     f"Failed to link: {result.stderr}")
                return

        # 2) Add all files
        result = subprocess.run(
            ['git', '-C', folder, 'add', '.'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if result.returncode != 0:
            messagebox.showerror("Git Error",
                                 f"Failed to add: {result.stderr}")
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
                messagebox.showerror("Git Error",
                                     f"Failed at commit: {result.stderr}")
                return
        else:
            set_status("NO CHANGES DETECTED")

        # 4) Set branch to main (default)
        result = subprocess.run(
            ['git', '-C', folder, 'branch', '-M', 'main'], # Auto-renames branch to 'main'
            capture_output=True, text=True, creationflags=startup_flags
        )
        if result.returncode != 0:
            messagebox.showerror("Git Error",
                                 f"Failed to set branch: {result.stderr}")
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
                messagebox.showerror("Git Error",
                                     f"Failed to add remote: {result.stderr}")
                return
        else:
            result = subprocess.run(
                ['git', '-C', folder, 'remote', 'set-url', 'origin', url],
                capture_output=True, text=True, creationflags=startup_flags
            )
            if result.returncode != 0:
                messagebox.showerror("Git Error",
                                     f"Failed to update remote: {result.stderr}")
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
                messagebox.showwarning("Pull Warning",
                                       f"Pull had issues:\n{pull_result.stderr}")
        else:
            set_status("REMOTE EMPTY > PUSHING...")

        # 6) Push
        set_status("PUSHING...")
        result = subprocess.run(
            ['git', '-C', folder, 'push', '-u', 'origin', 'main'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if result.returncode != 0:
            messagebox.showerror("Git Error",
                                 f"Failed at push: {result.stderr}")
            return

        app_state.save_history(folder)
        elapsed = end_timer(timer_start)
        set_status("INITIALIZE SUCCESS")
        messagebox.showinfo("Success",
                            f"Initialization finished!\n\n"
                            f"Process finished in {elapsed}.")
        branches = fetch_branches_from_repo(folder)
        if branches:
            all_branches = branches
            all_branches.sort()
            if 'main' in all_branches:
                all_branches.remove('main')
                all_branches.insert(0, 'main')
            branch_entry['values'] = all_branches
            merge_from_entry['values'] = all_branches
            merge_to_entry['values'] = all_branches
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
        messagebox.showwarning("Input",
                               "Please fill up all entry fields.")
        return

    set_processing(True, status_txt="CHECKING UNPUSHED")
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
            elapsed = end_timer(timer_start)
            set_status("Found unpushed commits - pushing...")
            messagebox.showinfo("Success",
                                f"Commits have been pushed!\n\n"
                                f"Process finished in {elapsed}.")
            return

        # 2.1) Check uncommitted changes
        status = subprocess.run(
            ['git', '-C', folder, 'status', '--porcelain'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if status.stdout.strip(): # 2.2) If has uncommitted changes
            commit_changes(silent=True)
            push_to_github(silent=True)
            elapsed = end_timer(timer_start)
            set_status("PUSHING...")
            messagebox.showinfo("Success",
                                f"Changes have been committed and pushed!\n\n"
                                f"Process finished in {elapsed}.")
        else:
            set_status("NO CHANGES DETECTED")
            messagebox.showinfo("Status",
                                "No changes detected.")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        set_processing(False)

def commit_changes(silent=False):
    """Add > Commit"""
    folder = folder_var.get().strip()
    msg = msg_var.get().strip()

    if not msg:
        messagebox.showwarning("Input",
                               "Please enter a commit message.")
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
                messagebox.showinfo("Status",
                                    "No changes to commit.")
            set_status("NO CHANGES DETECTED")
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
            set_status("PUSH-READY")
            if not silent:
                elapsed = end_timer(timer_start)
                messagebox.showinfo("Success",
                                    f"Changes have been committed!\n\n"
                                    f"Process finished in {elapsed}.")
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
                    messagebox.showerror("Git Error",
                                         f"Could not create branch '{branch}':\n{create_res.stderr}")
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
                    messagebox.showerror("Git Error",
                                         f"Could not switch to branch '{branch}':\n{checkout_res.stderr}")
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
                messagebox.showerror("Push Blocked",
                                     f"Uncommitted changes detected! Please commit them first.\n\n"
                                     f"Process finished in {elapsed}.")
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
                    set_status("NO CHANGES DETECTED")
                    messagebox.showinfo("Push Status",
                                        "Everything is already up to date!")
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
            if not silent:
                elapsed = end_timer(timer_start)
                set_status("REPOSITORY UPDATED")
                messagebox.showinfo("Success",
                                    f"Commits have been pushed!\n\n"
                                    f"Process finished in {elapsed}.")
        else:
            if "rejected" in result.stderr.lower():
                if not silent:
                    set_status("PUSH REJECTED > PULL NEEDED")
                    messagebox.showerror("Push Failed",
                                         "Remote has new commits!\n\n"
                                         "Click 'PULL' first, then try pushing again.")
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
        messagebox.showwarning("Input",
                               "Please enter a folder path.")
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
            messagebox.showinfo("Success",
                                f"Latest changes pulled from '{branch}'!\n\n"
                                f"Process finished in {elapsed}.")
            branches = fetch_branches_from_repo(folder)

            if branches:
                all_branches = branches
                all_branches.sort()
                if 'main' in all_branches:
                    all_branches.remove('main')
                    all_branches.insert(0, 'main')
                branch_entry['values'] = all_branches
                merge_from_entry['values'] = all_branches
                merge_to_entry['values'] = all_branches
        else:
            if "no such remote" in result.stderr.lower():
                set_status("NO REMOTE FOUND")
                messagebox.showerror("Pull Failed",
                                     "No remote 'origin' found. Link the repo first.")
            else:
                set_status("PULL FAILED")
                messagebox.showerror("Pull Failed", result.stderr)
    except Exception as e:
        elapsed = end_timer(timer_start)
        messagebox.showerror("Error", str(e))
    finally:
        set_processing(False)

# BRANCH COMMANDS ###############################################################################################################

def create_branch():
    """Create a new branch from current branch"""
    folder = folder_var.get().strip()
    new_branch = branch_name_var.get().strip()

    if not folder:
        messagebox.showwarning("Input",
                               "Please enter a folder path.")
        return
    if not new_branch:
        messagebox.showwarning("Input",
                               "Please enter a branch name.")
        return
    if not validate_environment(folder):
        return

    # 1) Check for uncommitted changes
    status = subprocess.run(
        ['git', '-C', folder, 'status', '--porcelain'],
        capture_output=True, text=True, creationflags=startup_flags
    )
    if status.stdout.strip():
        confirm = messagebox.askyesno(
            "Uncommitted Changes",
            "You have uncommitted changes. They will be carried over to the new branch.\n\nContinue?"
        )
        if not confirm:
            set_status("CREATE CANCELLED")
            return

        # 2) Check if branch already exists locally
        branch_check = subprocess.run(
            ['git', '-C', folder, 'rev-parse', '--verify', new_branch],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if branch_check.returncode == 0:
            messagebox.showerror("Error",
                                 f"Branch '{new_branch}' already exists locally!")
            return

        set_processing(True, status_txt=f"CREATING BRANCH: {new_branch}")
        timer_start = start_timer()

    try:
        # 3) Create and switch to new branch locally
        result = subprocess.run(
            ['git', '-C', folder, 'checkout', '-b', new_branch],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if result.returncode != 0:
            messagebox.showerror("Git Error",
                                 f"Failed to create branch:\n{result.stderr}")
            return

        # 4) Push to remote and set upstream
        push_result = subprocess.run(
            ['git', '-C', folder, 'push', '-u', 'origin', new_branch],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if push_result.returncode != 0:
            messagebox.showerror("Git Error",
                                 f"Failed to push branch to remote:\n{push_result.stderr}")
            return

        elapsed = end_timer(timer_start)
        set_status(f"BRANCH CREATED: {new_branch}")
        messagebox.showinfo("Success",
                            f"Branch '{new_branch}' created and pushed to remote!\n\n"
                            f"Process finished in {elapsed}.")

        # 5) Update dropdowns
        branches = fetch_branches_from_repo(folder)
        if branches:
            all_branches = branches
            all_branches.sort()
            if 'main' in all_branches:
                all_branches.remove('main')
                all_branches.insert(0, 'main')
            branch_entry['values'] = all_branches
            merge_from_entry['values'] = all_branches
            merge_to_entry['values'] = all_branches
            branch_var.set(new_branch)
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        set_processing(False)

def delete_branch():
    """Delete a branch (local and remote)"""
    folder = folder_var.get().strip()
    branch = branch_name_var.get().strip()

    if not folder:
        messagebox.showwarning("Input", "Please enter a folder path.")
        return
    if not branch:
        messagebox.showwarning("Input", "Please enter a branch name.")
        return
    if branch == "main":
        messagebox.showerror("Error", "Cannot delete 'main' branch!")
        return
    if not validate_environment(folder):
        return

    # 1) Check if branch exists
    branch_check = subprocess.run(
        ['git', '-C', folder, 'rev-parse', '--verify', branch],
        capture_output=True, text=True, creationflags=startup_flags
    )
    if branch_check.returncode != 0:
        messagebox.showerror("Error",
                             f"Branch '{branch}' does not exist!")
        return

    # 2.1) Check if currently on this branch
    current_branch = subprocess.run(
        ['git', '-C', folder, 'rev-parse', '--abbrev-ref', 'HEAD'],
        capture_output=True, text=True, creationflags=startup_flags
    ).stdout.strip()

    if current_branch == branch:
        # 2.2) Switch to main first
        subprocess.run(
            ['git', '-C', folder, 'checkout', 'main'],
            capture_output=True, text=True, creationflags=startup_flags
        )

    # 3) Confirm
    confirm = messagebox.askyesno(
        "Confirm Delete",
        f"Delete branch '{branch}'?\n\n"
        f"This will delete the local branch and remote branch (if it exists)."
    )
    if not confirm:
        set_status("DELETE CANCELLED")
        return

    set_processing(True, status_txt=f"DELETING BRANCH: {branch}")
    timer_start = start_timer()

    try:
        # 4.1) Delete local branch
        result_local = subprocess.run(
            ['git', '-C', folder, 'branch', '-D', branch],
            capture_output=True, text=True, creationflags=startup_flags
        )

        # 4.2) Delete remote branch if it exists
        remote_check = subprocess.run(
            ['git', '-C', folder, 'ls-remote', 'origin', branch],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if remote_check.stdout.strip():
            result_remote = subprocess.run(
                ['git', '-C', folder, 'push', 'origin', '--delete', branch],
                capture_output=True, text=True, creationflags=startup_flags
            )

        elapsed = end_timer(timer_start)
        set_status(f"BRANCH DELETED: {branch}")
        messagebox.showinfo("Success",
                            f"Branch '{branch}' deleted!\n\n"
                            f"Process finished in {elapsed}.")

        # 5) Update dropdowns
        branches = fetch_branches_from_repo(folder)
        if branches:
            all_branches = branches
            all_branches.sort()
            if 'main' in all_branches:
                all_branches.remove('main')
                all_branches.insert(0, 'main')
            branch_entry['values'] = all_branches
            merge_from_entry['values'] = all_branches
            merge_to_entry['values'] = all_branches
            branch_var.set('main')
        branch_name_var.set('')
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        set_processing(False)


def merge_branch():
    """Merge one branch into another"""
    folder = folder_var.get().strip()
    from_branch = merge_from_var.get().strip()
    to_branch = merge_to_var.get().strip()

    if not folder:
        messagebox.showwarning("Input", "Please enter a folder path.")
        return
    if not from_branch or not to_branch:
        messagebox.showwarning("Input", "Please select both 'From' and 'To' branches.")
        return
    if from_branch == to_branch:
        messagebox.showerror("Error", "Cannot merge a branch into itself!")
        return
    if not validate_environment(folder):
        return

    # 1) Check for uncommitted changes in current branch
    status = subprocess.run(
        ['git', '-C', folder, 'status', '--porcelain'],
        capture_output=True, text=True, creationflags=startup_flags
    )
    if status.stdout.strip():
        confirm = messagebox.askyesno(
            "Uncommitted Changes",
            "You have uncommitted changes. Merging with uncommitted changes may cause conflicts.\n\nContinue anyway?"
        )
        if not confirm:
            set_status("MERGE CANCELLED")
            return

    # 2) Confirm
    confirm = messagebox.askyesno(
        "Confirm Merge",
        f"Merge '{from_branch}' INTO '{to_branch}'?\n\n"
        "This will combine the changes from both branches."
    )
    if not confirm:
        set_status("MERGE CANCELLED")
        return

    set_processing(True, status_txt=f"MERGING {from_branch} → {to_branch}")
    timer_start = start_timer()

    try:
        # 3) Switch to target branch
        checkout_res = subprocess.run(
            ['git', '-C', folder, 'checkout', to_branch],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if checkout_res.returncode != 0:
            messagebox.showerror("Git Error",
                                 f"Could not switch to '{to_branch}':\n{checkout_res.stderr}")
            return

        # 4.1) Merge
        result = subprocess.run(
            ['git', '-C', folder, 'merge', from_branch],
            capture_output=True, text=True, creationflags=startup_flags
        )
        if result.returncode == 0:
            elapsed = end_timer(timer_start)
            set_status(f"MERGE SUCCESS: {from_branch} → {to_branch}")
            messagebox.showinfo("Success",
                                f"Merged '{from_branch}' INTO '{to_branch}'!\n\nProcess finished in {elapsed}.")
            # 4.2) Push the merged branch
            push_to_github(silent=True)
        else:
            if "merge conflict" in result.stderr.lower():
                messagebox.showerror("Merge Conflict",
                                     f"Merge conflict detected!\n\n"
                                     "Please resolve conflicts manually in your editor, then commit and push.")
            else:
                messagebox.showerror("Git Error",
                                     f"Merge failed:\n{result.stderr}")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        set_processing(False)

# OTHER ################################################################################################################

def set_folder(path):
    """Set folder from history chip"""
    if path and path.strip():
        folder_var.set(path)
        app_state.save_history(path)
        validate_fields()

def fetch_branches_from_repo(folder):
    """Get all existing branches"""
    try:
        # 1.1) Get local branches
        local_result = subprocess.run(
            ['git', '-C', folder, 'branch', '--format=%(refname:short)'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        local_branches = [b.strip() for b in local_result.stdout.splitlines() if b.strip()]

        # 1.2) Get remote branches
        remote_result = subprocess.run(
            ['git', '-C', folder, 'branch', '-r', '--format=%(refname:short)'],
            capture_output=True, text=True, creationflags=startup_flags
        )
        remote_branches = [b.strip().replace('origin/', '') for b in remote_result.stdout.splitlines() if b.strip()]

        # 2) Combine
        all_branches = list(set(local_branches + remote_branches))
        all_branches = [b for b in all_branches if b != 'HEAD' and not b.endswith('HEAD')]
        all_branches.sort()
        return all_branches
    except Exception: return []

def show_help():
    """Show help messagebox"""
    messagebox.showinfo(
        "QuikBash Help",
        "QUIKBASH QUICK GUIDE\n"
        "=============================\n\n"
        "SETUP\n"
        "  • LINK - Initialize or re-link a repository\n"
        "  • RE-LINK - Reconnect a previously linked repo\n\n"
        "WORK\n"
        "  • COMMIT - Save changes locally\n"
        "  • PUSH   - Upload commits to remote\n"
        "  • COMMIT & PUSH - Commit and push in one click\n"
        "  • PULL - Download latest changes from remote\n\n"
        "BRANCH\n"
        "  • CREATE - Create and push a new branch\n"
        "  • DELETE - Remove a branch (local & remote)\n"
        "  • MERGE - Combine branches (FROM → TO)"
    )

# INTERFACE ############################################################################################################

# Base
root = tk.Tk()
root.title("QuikBash 3.8")
root.geometry("425x460")
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
branch_name_var = tk.StringVar()
merge_to_var = tk.StringVar()
merge_from_var = tk.StringVar()

# Button State
folder_var.trace_add("write", validate_fields)
url_var.trace_add("write", validate_fields)
msg_var.trace_add("write", validate_fields)
branch_name_var.trace_add("write", validate_fields)
merge_from_var.trace_add("write", validate_fields)
merge_to_var.trace_add("write", validate_fields)

# Folder Path
ttk.Label(root, text="Folder Path:", font=('Arial', 10, 'bold')).pack(pady=(20, 0))
folder_entry = ttk.Combobox(root, width=50, textvariable=folder_var)
folder_entry.pack(pady=(5, 30), padx=20, fill=tk.X)
folder_entry['values'] = app_state.history

# Tab Setup
tab_control = ttk.Notebook(root)
tab1 = ttk.Frame(tab_control, padding=10)
tab2 = ttk.Frame(tab_control, padding=10)
tab3 = ttk.Frame(tab_control, padding=10)
tab_control.add(tab1, text="SETUP")
tab_control.add(tab2, text="WORK")
tab_control.add(tab3, text="BRANCH")
tab_control.pack(expand=True, fill="both", padx=10)

status_var = tk.StringVar(value="READY")

# Tab 1 (New Repo)
ttk.Label(tab1, text="Remote URL:").pack(pady=(10, 0))
url_entry = ttk.Entry(tab1, textvariable=url_var)
url_entry.pack(pady=5, fill=tk.X)

init_button = ttk.Button(tab1, text="LINK", command=lambda: run_async(init_new_repo), state="disabled")
init_button.pack(fill=tk.X, pady=5)

ttk.Frame(tab1).pack(expand=True, fill=tk.BOTH)
ttk.Label(tab1, textvariable=status_var, style="Status.TLabel", anchor="center", font=('Arial', 9, 'bold')).pack(fill=tk.X, pady=(10, 0))

# Tab 2 (Update Repo)
ttk.Label(tab2, text="Branch:").pack(pady=(10, 0))
branch_entry = ttk.Combobox(tab2, width=50, textvariable=branch_var)
branch_entry.pack(pady=5, fill=tk.X)
branch_entry['values'] = []
branch_var.set("main")

ttk.Label(tab2, text="Message:").pack(pady=(10, 0))
commit_entry = ttk.Entry(tab2, textvariable=msg_var)
commit_entry.pack(pady=5, fill=tk.X)

tab2_frame = ttk.Frame(tab2)
tab2_frame.pack(pady=5, fill=tk.X)
tab2_frame.columnconfigure(0, weight=1, uniform="a")
tab2_frame.columnconfigure(1, weight=1, uniform="a")

anc_button = ttk.Button(tab2_frame, text="COMMIT", command=lambda: run_async(commit_changes), state="disabled")
anc_button.grid(row=0, column=0, padx=(0, 5), pady=(0, 5), sticky="ew")
push_button = ttk.Button(tab2_frame, text="PUSH", command=lambda: run_async(push_to_github), state="disabled")
push_button.grid(row=0, column=1, padx=(5, 0), pady=(0, 5), sticky="ew")
sync_button = ttk.Button(tab2_frame, text="COMMIT & PUSH", command=lambda: run_async(do_all), state="disabled")
sync_button.grid(row=1, column=0, padx=(0, 5), pady=(5, 0), sticky="ew")
pull_button = ttk.Button(tab2_frame, text="PULL", command=lambda: run_async(pull_from_github), state="disabled")
pull_button.grid(row=1, column=1, padx=(5, 0), pady=(5, 0), sticky="ew")

ttk.Frame(tab2).pack(expand=True, fill=tk.BOTH)
ttk.Label(tab2, textvariable=status_var, style="Status.TLabel", anchor="center", font=('Arial', 9, 'bold')).pack(fill=tk.X, pady=(10, 0))

# Tab 3 (Branch Controls)
ttk.Label(tab3, text="Branch Name:").pack(pady=(10, 0))
branch_name_entry = ttk.Entry(tab3, textvariable=branch_name_var)
branch_name_entry.pack(pady=5, fill=tk.X)

tab3_frame = ttk.Frame(tab3)
tab3_frame.pack(pady=5, fill=tk.X)
tab3_frame.columnconfigure(0, weight=1, uniform="a")
tab3_frame.columnconfigure(1, weight=1, uniform="a")

create_button = ttk.Button(tab3_frame, text="CREATE", command=lambda: run_async(create_branch), state="disabled")
create_button.grid(row=0, column=0, padx=(0, 5), pady=(0, 2), sticky="ew")
delete_button = ttk.Button(tab3_frame, text="DELETE", command=lambda: run_async(delete_branch), state="disabled")
delete_button.grid(row=0, column=1, padx=(5, 0), pady=(0, 2), sticky="ew")

merge_frame = ttk.Frame(tab3)
merge_frame.pack(pady=5, fill=tk.X)
merge_frame.columnconfigure(0, weight=1, uniform="a")
merge_frame.columnconfigure(1, weight=0)
merge_frame.columnconfigure(2, weight=1, uniform="a")

merge_from_entry = ttk.Combobox(merge_frame, textvariable=merge_from_var)
merge_from_entry.grid(row=0, column=0, padx=(0, 5), sticky="ew")
merge_from_entry['values'] = []

ttk.Label(merge_frame, text="→", font=('Arial', 16, 'bold')).grid(row=0, column=1, padx=3)

merge_to_entry = ttk.Combobox(merge_frame, textvariable=merge_to_var)
merge_to_entry.grid(row=0, column=2, padx=(5, 0), sticky="ew")
merge_to_entry['values'] = []

merge_button = ttk.Button(tab3, text="MERGE", command=lambda: run_async(merge_branch), state="disabled")
merge_button.pack(fill=tk.X, pady=5)

ttk.Frame(tab3).pack(expand=True, fill=tk.BOTH)
ttk.Label(tab3, textvariable=status_var, style="Status.TLabel", anchor="center", font=('Arial', 9, 'bold')).pack(fill=tk.X, pady=(10, 0))

# Help
help_frame = ttk.Frame(root)
help_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))
help_button = ttk.Button(help_frame, text="?", width=3, command=lambda: show_help())
help_button.pack(side=tk.RIGHT)

# Copyright
version_label = ttk.Label(help_frame, text="kriscow © 2026", font=('Arial', 8), foreground='gray')
version_label.pack(side=tk.LEFT)

validate_fields()
root.mainloop()

# TODO
#  merge confirmation
#  worktree