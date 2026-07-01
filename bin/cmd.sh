#! /usr/bin/env bash
# Start the service.


set -eo pipefail


# if [ -z "$USB_VENDOR_ID" ]; then
#     printf "ERROR: USB_VENDOR_ID is not defined. Please provide a valid USB vendor ID in hexadecimal (from lsusb -v output).\\n" >&2
#     exit 1
# fi

# if [ -z "$USB_PRODUCT_ID" ]; then
#     printf "ERROR: USB_PRODUCT_ID is not defined. Please provide a valid USB product ID in hexadecimal (from lsusb -v output).\\n" >&2
#     exit 1
# fi

# Start the service.
if command -v poetry >/dev/null 2>&1 && poetry env info -p >/dev/null 2>&1; then
    exec poetry run orchidarium "$@"
else
    exec orchidarium "$@"
fi
