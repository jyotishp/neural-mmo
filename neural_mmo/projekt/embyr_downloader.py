import os
import zipfile
from pathlib import Path
import shutil
from urllib.request import urlretrieve
from tqdm import tqdm
import neural_mmo


CLIENT_REPO_URL = "https://github.com/jsuarez5341/neural-mmo-client"
VERSION = ".".join(neural_mmo.__version__.split(".")[:3])
PACKAGE_DIR = Path(neural_mmo.__file__).resolve().parent


class TqdmHook(tqdm):
    def update_to(self, blocks_completed=1, block_size=1, total_size=None):
        if total_size is not None:
            self.total = total_size
        self.update(blocks_completed * block_size - self.n)


def download_file(url, save_dir):
    filename = url.split("/")[-1]
    target_filename = os.path.join(save_dir, filename)
    print(f"Downloading {url} -> {target_filename}")
    with TqdmHook(
        unit="B", unit_scale=True, unit_divisor=1024, miniters=1, desc=filename
    ) as t:
        urlretrieve(url, filename=target_filename, reporthook=t.update_to)
    print("Download complete!")
    return target_filename


def extract_zip(zip_file, target_dir):
    print(f"Extracting {zip_file} -> {target_dir}")
    with zipfile.ZipFile(zip_file, "r") as zip_ref:
        zip_ref.extractall(target_dir)
    print("Extraction complete")


def setup_neural_mmo_client():
    client_archive = None
    client_version = os.getenv("CLIENT_VERSION", VERSION)
    extracted_client_path = f"neural-mmo-client-{client_version}"

    try:
        client_url = f"{CLIENT_REPO_URL}/archive/refs/heads/v{client_version}.zip"
        client_archive = download_file(client_url, PACKAGE_DIR)
        extract_zip(client_archive, PACKAGE_DIR)

        print("Copying files to python site-package")
        target_path = str(PACKAGE_DIR / "forge/embyr")
        shutil.copytree(extracted_client_path, target_path, dirs_exist_ok=True)

    except Exception as e:
        raise e

    finally:
        if client_archive is None:
            return
        if os.path.exists(client_archive):
            os.remove(client_archive)
        if os.path.exists(extracted_client_path):
            shutil.rmtree(extracted_client_path)
