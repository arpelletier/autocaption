# import logging
#
#
# def setup_logger(log_file_name='./log/log.txt'):
#     # Create or get the logger
#     logger = logging.getLogger("autocaption")
#     logger.setLevel(logging.DEBUG)  # Set the minimum level of logs to handle
#
#     # Create handlers (e.g., console, file)
#     console_handler = logging.StreamHandler()
#     file_handler = logging.FileHandler(log_file_name)
#
#     # Set levels for handlers (optional)
#     console_handler.setLevel(logging.INFO)
#     file_handler.setLevel(logging.DEBUG)
#
#     # Create formatters and add to handlers
#     formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     console_handler.setFormatter(formatter)
#     file_handler.setFormatter(formatter)
#
#     # Add handlers to the logger
#     if not logger.handlers:  # Prevent adding handlers multiple times
#         logger.addHandler(console_handler)
#         logger.addHandler(file_handler)
#
#     return logger


import logging

def setup_logger(log_file_name='./log/log.txt'):
    logger = logging.getLogger("autocaption")
    logger.setLevel(logging.DEBUG)  # Set the minimum level of logs to handle

    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create handlers (e.g., console, file)
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(log_file_name)

    # Set levels for handlers (optional)
    console_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.DEBUG)

    # Create formatters and add to handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
