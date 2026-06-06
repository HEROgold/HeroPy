from __future__ import annotations

import sys

if sys.version_info >= (3, 14):
    '''

    from herogold.log import FileHandler, Logger, StreamHandler

    def test_314_loggings() -> None:
        """Usage of the custom Logger."""
        logger = Logger("herogold")
        logger.addHandler(StreamHandler())
        logger.addFilter(FileHandler("herogold.log"))
        world = "world"
        number = 42.159
        item = "something"
        error = "an error message"
        logger.info(t"Hello, {world}!")
        logger.debug(t"This is a debug message with a number: {number}")
        logger.warning(t"This is a warning about {item}.")
        logger.error(t"An error occurred: {error}")
        try:
            1 / 0  # noqa: B018
        except ZeroDivisionError:
            logger.exception(t"Caught an exception.")
    '''
