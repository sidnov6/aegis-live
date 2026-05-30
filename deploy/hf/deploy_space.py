"""Deploy the AEGIS Live backend to a Hugging Face Docker Space.

Assembles a Space bundle from the existing backend (single source of truth) and
uploads it via the HF Hub API. Requires an HF write token.

Usage:
    HF_TOKEN=hf_xxx python deploy/hf/deploy_space.py [--name aegis-live-backend]

It creates (or reuses) the Space, uploads Dockerfile + README + requirements +
aegis/ + lists/, and prints the live URL.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HF_DIR = os.path.join(REPO_ROOT, "deploy", "hf")


def build_bundle(dst: str) -> None:
    shutil.copy(os.path.join(HF_DIR, "Dockerfile"), os.path.join(dst, "Dockerfile"))
    shutil.copy(os.path.join(HF_DIR, "README.md"), os.path.join(dst, "README.md"))
    shutil.copy(os.path.join(REPO_ROOT, "backend", "requirements.txt"),
                os.path.join(dst, "requirements.txt"))
    shutil.copytree(os.path.join(REPO_ROOT, "backend", "aegis"),
                    os.path.join(dst, "aegis"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(os.path.join(REPO_ROOT, "lists"), os.path.join(dst, "lists"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="aegis-live-backend")
    args = ap.parse_args()

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    if not token:
        print("ERROR: set HF_TOKEN (an HF write token) in the environment.")
        return 2

    from huggingface_hub import HfApi

    api = HfApi(token=token)
    who = api.whoami()
    user = who["name"]
    repo_id = f"{user}/{args.name}"
    print(f"Deploying to Space: {repo_id}")

    api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="docker",
                    exist_ok=True, token=token)

    with tempfile.TemporaryDirectory() as tmp:
        build_bundle(tmp)
        api.upload_folder(folder_path=tmp, repo_id=repo_id, repo_type="space",
                          token=token, commit_message="Deploy AEGIS Live backend")

    url = f"https://huggingface.co/spaces/{repo_id}"
    api_base = f"https://{user.lower()}-{args.name}.hf.space"
    print("\n=== DEPLOYED ===")
    print(f"Space:    {url}")
    print(f"API base: {api_base}")
    print(f"Health:   {api_base}/api/health")
    print(f"WS:       {api_base.replace('https','wss')}/ws")
    print("\nThe Space will build the Docker image (a few minutes) then go live.")
    print(f"Set the UI env: NEXT_PUBLIC_API_BASE={api_base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
