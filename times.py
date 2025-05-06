import os
import subprocess

# Configuration
REPO_PATH = "/Users/paulodrefahl/Desktop/Projects/medeyeai"  # Replace with your GitHub repo path
COMMIT_MESSAGE = "Medeye 1.1v"  # Commit message
COMMIT_DATE = "2025-05-06T08:00:00"  # Format: YYYY-MM-DDTHH:MM:SS
BRANCH_NAME = "main"  # Replace if your branch is different

def run_command(command, cwd=None, env=None):
    """Run a shell command and capture the output."""
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr.strip()}")
        exit(1)
    return result.stdout.strip()

def main():
    # Ensure repository path exists
    if not os.path.exists(REPO_PATH):
        print(f"Error: Repository path '{REPO_PATH}' does not exist.")
        return
    os.chdir(REPO_PATH)

    # Add changes
    print("Adding changes...")
    run_command(["git", "add", "."], cwd=REPO_PATH)

    # Check if there is anything to commit
    status_output = run_command(["git", "status", "--porcelain"], cwd=REPO_PATH)
    if not status_output:
        print("No changes to commit.")
        return

    # Commit changes with a custom date
    print("Committing changes...")
    env = os.environ.copy()
    env["GIT_COMMITTER_DATE"] = COMMIT_DATE
    run_command([
        "git", "commit", "--date", COMMIT_DATE, "-m", COMMIT_MESSAGE
    ], cwd=REPO_PATH, env=env)

    # Pull latest remote changes before pushing
    print("Pulling latest changes from GitHub...")
    run_command(["git", "pull", "--rebase", "origin", BRANCH_NAME], cwd=REPO_PATH)

    # Push changes
    print("Pushing changes to GitHub...")
    run_command(["git", "push", "origin", BRANCH_NAME], cwd=REPO_PATH)

    print("✅ Changes successfully committed and pushed to GitHub.")

if __name__ == "__main__":
    main()
