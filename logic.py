import git
import os
import yaml
import json
import requests
import time
import subprocess

CONFIG_FILE = "config.yaml"
IG_SOURCE_FILE = "ig_source.yaml"

def load_config(file_path):
    """Load YAML configuration."""
    try:
        with open(file_path, "r") as file:
            return yaml.safe_load(file) or {}
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}

def fetch_or_update_repo(repo_url, dest_folder, timeout=60):
    """Clone or update a repository with a timeout handling."""
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    try:
        if os.path.exists(os.path.join(dest_folder, ".git")):
            repo = git.Repo(dest_folder)
            print(f"🔄 Fetching updates for {repo_url}...")
            start_time = time.time()

            # Instead of using an unsupported --timeout, use a subprocess with a timeout
            fetch_process = subprocess.Popen(["git", "fetch", "--all"], cwd=dest_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                fetch_process.wait(timeout=timeout)  # ✅ Manually enforce timeout
            except subprocess.TimeoutExpired:
                fetch_process.kill()
                print(f"❌ Fetching {repo_url} timed out after {timeout} seconds.")
                return False

            elapsed_time = time.time() - start_time
            print(f"✅ Repository {repo_url} updated in {elapsed_time:.2f} seconds.")
        else:
            print(f"📥 Cloning {repo_url} into {dest_folder}...")
            start_time = time.time()

            git.Repo.clone_from(repo_url, dest_folder)

            elapsed_time = time.time() - start_time
            print(f"✅ Cloned {repo_url} in {elapsed_time:.2f} seconds.")
        return True
    except Exception as e:
        print(f"❌ Error fetching {repo_url}: {e}")
        return False

def get_git_branches(repo_url):
    """Retrieve all branches and tags from the IG source repository."""
    try:
        repo_refs = git.cmd.Git().ls_remote("--heads", repo_url)
        branch_list = [line.split("\t")[1].replace("refs/heads/", "") for line in repo_refs.splitlines()]

        repo_tags = git.cmd.Git().ls_remote("--tags", repo_url)
        tag_list = [line.split("\t")[1].replace("refs/tags/", "") for line in repo_tags.splitlines()]

        return branch_list + tag_list  # Combine branches & tags
    except Exception as e:
        print(f"Error fetching branches/tags from {repo_url}: {e}")
        return []

def switch_to_branch(repo_path, branch):
    """Switch to a selected branch in the cloned repository."""
    try:
        repo = git.Repo(repo_path)
        repo.git.fetch("--all")
        repo.git.checkout(branch)
        return True
    except Exception as e:
        print(f"Failed to switch to branch {branch}: {e}")
        return False

def load_publication_request(repo_path):
    """Load publication-request.json if it exists, otherwise return empty JSON."""
    json_path = os.path.join(repo_path, "publication-request.json")

    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            print(f"Failed to load publication-request.json: {e}")
            return "{}"
    return "{}"



def gh_pages_has_sitepreview(repo_url):
    """Check if the gh-pages branch contains a sitepreview folder."""
    try:
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        user_name = repo_url.split("/")[-2]
        gh_pages_url = f"https://raw.githubusercontent.com/{user_name}/{repo_name}/gh-pages/sitepreview/index.html"

        response = requests.head(gh_pages_url, allow_redirects=True)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error checking gh-pages sitepreview: {e}")
        return False

def download_gh_pages(repo_url, work_folder):
    """Clone the gh-pages branch into the work folder if sitepreview exists."""
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    dest_folder = os.path.join(work_folder, "New_IG_Source")

    try:
        if os.path.exists(os.path.join(dest_folder, ".git")):
            repo = git.Repo(dest_folder)
            repo.git.fetch("--all")
            repo.git.checkout("gh-pages")
            print(f"✅ Downloaded gh-pages branch to {dest_folder}")
        else:
            git.Repo.clone_from(repo_url, dest_folder, branch="gh-pages")
            print(f"✅ Cloned gh-pages branch into {dest_folder}")
    except Exception as e:
        print(f"❌ Failed to clone gh-pages: {e}")

def deploy_built(current_web_content):
    """Deploy the built IG."""
    repo = git.Repo(current_web_content)
    repo.git.add("--all")
    repo.index.commit("🚀 Deploying Built IG")
    repo.git.push("origin", "main")
    print("✅ Built IG Deployed!")

def deploy_prebuilt(current_web_content, work_folder):
    """Deploy the pre-built IG by copying `sitepreview` to `Current_Web_Content`."""
    sitepreview_path = os.path.join(work_folder, "New_IG_Source", "sitepreview")

    if not os.path.exists(sitepreview_path):
        print("❌ No pre-built IG found in sitepreview.")
        return False

    print(f"📥 Copying sitepreview contents to {current_web_content}...")
    shutil.copytree(sitepreview_path, current_web_content, dirs_exist_ok=True)

    # Initialize Git & Create a new PR branch
    repo = git.Repo(current_web_content)
    repo.git.add("--all")
    repo.index.commit("🚀 Deploying Pre-Built IG")
    repo.create_head("new")
    repo.git.push("origin", "new")

    print("✅ Pre-Built IG deployed. PR 'new' created!")
    return True