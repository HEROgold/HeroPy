
try:
    import watchdog
except ImportError as e:
    msg = (
        "Failed to import required dependencies for the database package. "
        "Please ensure that 'services' extra is installed. "
        "You can install them using 'herogold[services]'."
    )
    raise ImportError(msg) from e
