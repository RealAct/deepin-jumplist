#!/bin/sh
# Launcher installed as deepin-jumplist on the PATH.
# @LIBDIR@ is replaced at install time with the folder holding the package.
PYTHONPATH="@LIBDIR@${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m deepin_jumplist "$@"
