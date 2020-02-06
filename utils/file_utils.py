import os


class FileNameOps:

    @staticmethod
    def build_filename(target_dir: str, input_fname: str, ext: str) -> str:
        """
        Builds the out file name, based on desired directory and extension, using the filename of the input file
        (minus the file extension)

        :param target_dir: (str) relative path to the directory to write the file
        :param input_fname: (str) name of input file
        :param ext: (str) file extension to append to the out file

        :return: (str) full absolute-path file spec

        """
        # Get the input filename, minus any file path (/this/direct/file.ext --> file.ext)
        input_fname = input_fname.split(os.path.sep)[-1]

        # Get the input filename, minus the extension, and append the provided extension.
        input_fname = f"{'.'.join(input_fname.split('.')[:-1])}.{ext}"

        # Build the complete file spec and return as an absolute path
        return os.path.abspath(os.path.sep.join(['.', target_dir, input_fname]))

    @staticmethod
    def build_filespec(src: str, dst: str, target_dir: str = '.', ext: str = "log", html: bool = False) -> str:
        """
        Builds the dir+name by combining the source file names (no ext) and adding a log file extension.
        :param src: Source XML file
        :param dst: Comparison XML file
        :param target_dir: directory to write file (relative or absolute directory path)
        :param ext: file extension - default: "log"
        :param html: (bool) - Build HTML filename

        :return: new file spec
        """
        extension = "html" if html else ext
        src_portion = ".".join(src.split(os.path.sep)[-1].split(".")[:-1])
        dst_portion = ".".join(dst.split(os.path.sep)[-1].split(".")[:-1])

        return os.path.abspath(os.path.sep.join([target_dir, f"comp_{src_portion}_{dst_portion}.{extension}"]))

    @classmethod
    def create_filename(cls, primary_filename, basis_filename, ext="rpt", target_dir=".", unique=True):
        """
        Create the requested filespec, and if the file exists, delete it (in the case where a filehandle needs to open
        in append mode, but it should be an empty file to start.

        :param primary_filename: Primary XML file
        :param basis_filename: Comparison XML file
        :param target_dir: directory to write file (relative or absolute directory path)
        :param ext: file extension - default: "rpt"
        :param unique: (bool) - If file already exists, delete

        :return: (str) filespec
        """
        target_filespec = cls.build_filespec(src=primary_filename, dst=basis_filename, ext=ext, target_dir=target_dir)
        if unique and os.path.exists(target_filespec):
            os.remove(target_filespec)
        return target_filespec
