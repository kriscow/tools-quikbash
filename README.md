# QUIKBASH
### A featherweight Git GUI to work without the bloat.

<p align="center">
    <img src="QB.png" alt="QuikBash Icon" width="200">
</p>

> Git workflows should not require opening a heavy, resource-intensive desktop application.
QuikBash is built to be fast and lightweight, focusing solely on the core commands needed for simple projects.
It is perfect for users who just want to get their repositories updated without the wait.

---

## 🟢 Overview
| Property         | Details      |               |
|:-----------------|:-------------|:--------------|
| **Developer**    | KRISCOW      | INDIE         |
| **Engine**       | Python       | 3.14.4        |
| **Format**       | Desktop Tool | EXE           |
| **Version**      | v5.0.stable  | FROZEN        |
| **Since**        | July 7, 2026 | Sept 23, 2026 |

#### QuikBash is now feature-complete and frozen. Further developments will be up to you, rockstar.

---

## 🟡 Features
### Core Operations
* Connect local and remote repositories.
* View existing commits and ignored files without leaving.
* The core stage, commit, and push commands that can be done in one click.
* Ability to create, delete, and merge branches.
* Important controls such as pull and undo commit.
### Quality of Life
* Jump to the repository in File Explorer.
* Quickly scan and select project paths through saved histories.
* Debounced input for instant typing.
* And other stuff you can discover-in-app!

---

## 🔵 Installation
### For Users
1. Download the latest **QuikBash.exe** from the [Releases](https://github.com/kriscow/quikbash-tool/releases) page.
2. Ensure [Git](https://git-scm.com/downloads) is installed on your PATH.
3. Simply run the application.

### For Developers
1. Clone this repository.
2. Install [Git](https://git-scm.com/downloads) and [Python](https://www.python.org/).
3. Install PyInstaller
```
py -m pip install pyinstaller
```
4. Build the executable:
```
py -m PyInstaller --noconfirm QuikBash.spec
```

---

**MIT License** / See [LICENSE](LICENSE) for details.