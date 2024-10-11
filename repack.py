import zipfile
import os
def zip_folder(folder_path, zip_filename):
    """Zips a folder and maintains the root folder name in the zip file."""

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(folder_path, os.path.basename(folder_path))

        for root, dirs, files in os.walk(folder_path):
            # Create a relative path for the zip file

            relative_root = os.path.join(os.path.basename(folder_path),os.path.relpath(root, folder_path))
            for file in files:
                file_path = os.path.join(root, file)
                # Add the file to the zip, using the relative path
                zipf.write(file_path, os.path.join(relative_root, file))
if __name__ == "__main__":
    foldername = os.path.dirname(__file__)
    folder_to_zip = f"{foldername}"
    output_zip_file = f"{foldername}.zip"
    zip_folder(folder_to_zip, output_zip_file)