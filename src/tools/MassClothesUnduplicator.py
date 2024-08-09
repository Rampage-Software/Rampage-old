import os
from Tool import Tool
from utils import Utils
import click
from hashlib import sha256

class MassClothesUnduplicator(Tool):
    def __init__(self, app):
        super().__init__("Mass Clothes Unduplicator", "Unduplicates your assets files", app)

        self.assets_files_directory = os.path.join(self.files_directory, "./assets")
        self.shirts_files_directory = os.path.join(self.files_directory, "./assets/shirts")
        self.pants_files_directory = os.path.join(self.files_directory, "./assets/pants")

        self.cache_template_path = os.path.join(self.cache_directory, "asset-template.png")

        Utils.ensure_directories_exist([self.assets_files_directory, self.shirts_files_directory, self.pants_files_directory])

    def run(self):
        self.remove_duplicates(self.shirts_files_directory)
        self.remove_duplicates(self.pants_files_directory)
        click.echo("Duplicate files unduplicated successfully.")

    def get_file_hash(self, file_path):
        hasher = sha256()
        with open(file_path, 'rb') as file:
            while chunk := file.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def remove_duplicates(self, folder_path):
        hash_dict = {}
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_hash = self.get_file_hash(file_path)
                if file_hash in hash_dict:
                    # Remove duplicate file
                    os.remove(file_path)
                    print(f"Duplicate file removed: {file_path}")
                else:
                    hash_dict[file_hash] = file_path
