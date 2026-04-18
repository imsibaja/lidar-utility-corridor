"""
Wrappers for executing PDAL pipeline JSON files from Python.
"""


def run_pipeline(pipeline_json_path, input_laz, output_laz):
    """
    Execute a PDAL pipeline JSON file with specified input and output paths.

    Reads the pipeline JSON, substitutes the PLACEHOLDER_INPUT and
    PLACEHOLDER_OUTPUT values with the provided paths, and executes the
    pipeline via the pdal Python bindings or subprocess. Raises on non-zero
    exit code or missing files.

    Parameters
    ----------
    pipeline_json_path : str or Path
        Path to a PDAL pipeline JSON file (e.g., pipeline/pdal_pipeline.json).
    input_laz : str or Path
        Path to the input .laz or .las file to be processed.
    output_laz : str or Path
        Desired output path for the normalized .laz file.

    Returns
    -------
    None

    Raises
    ------
    FileNotFoundError
        If pipeline_json_path or input_laz do not exist on disk.
    RuntimeError
        If the PDAL pipeline exits with a non-zero return code.
    """
    raise NotImplementedError


def check_pdal_available():
    """
    Verify that PDAL is installed and accessible from the current environment.

    Attempts to invoke `pdal --version` via subprocess and parses the version
    string. PDAL must be installed via conda-forge (not pip) due to system-level
    C++ library dependencies. Installation via pip is not supported.
    See: https://pdal.io/en/stable/development/compilation/index.html

    Returns
    -------
    str
        PDAL version string if the binary is found and responds correctly.

    Raises
    ------
    EnvironmentError
        If PDAL is not found on PATH or the version call fails.
    """
    raise NotImplementedError
