import subprocess

def exec(
    command: str,
    *args: str,
) -> tuple[str, str, int]:
    """Executes a shell command and returns the output and error messages."""
    process = subprocess.Popen(
        [command, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = process.communicate()
    return stdout.decode("utf-8"), stderr.decode("utf-8"), process.returncode
