import argparse
import logic
import os
import json

def fetch_repo(repo_url, work_folder):
    """Fetch a single repository."""
    dest_folder = os.path.join(work_folder, "New_IG_Source")
    success = logic.fetch_or_update_repo(repo_url, dest_folder)
    if success:
        print(f"✅ Successfully fetched {repo_url}")
    else:
        print(f"❌ Failed to fetch {repo_url}")

def list_branches(repo_url):
    """List available branches for a repository."""
    branches = logic.get_git_branches(repo_url)
    if branches:
        print("📂 Available branches:")
        for branch in branches:
            print(f"  - {branch}")
    else:
        print("❌ No branches found.")

def switch_branch(repo_url, work_folder, branch):
    """Switch to a selected branch in the repository."""
    repo_path = os.path.join(work_folder, "New_IG_Source")
    success = logic.switch_to_branch(repo_path, branch)
    if success:
        print(f"✅ Switched to branch: {branch}")
    else:
        print(f"❌ Failed to switch to branch: {branch}")

def validate_json(repo_path):
    """Validate publication-request.json."""
    json_content = logic.load_publication_request(repo_path)
    try:
        json.loads(json_content)
        print("✅ Valid JSON format")
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")

def cli_main():
    """CLI Mode for Repository Operations."""
    parser = argparse.ArgumentParser(description="FHIR IG Release CLI Interface")

    parser.add_argument("--fetch", help="Fetch a repository by URL")
    parser.add_argument("--work-folder", help="Set work folder", default=".")
    parser.add_argument("--list-branches", help="List branches for a repository")
    parser.add_argument("--switch-branch", help="Switch to a branch")
    parser.add_argument("--validate-json", help="Validate publication-request.json", action="store_true")

    args = parser.parse_args()

    if args.fetch:
        fetch_repo(args.fetch, args.work_folder)
    elif args.list_branches:
        list_branches(args.list_branches)
    elif args.switch_branch:
        if args.work_folder:
            switch_branch(args.list_branches, args.work_folder, args.switch_branch)
        else:
            print("❌ Please specify --work-folder")
    elif args.validate_json:
        validate_json(args.work_folder)

if __name__ == "__main__":
    cli_main()
