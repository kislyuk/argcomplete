_python_argcomplete_global() {
    if which "$1" >/dev/null 2>/dev/null && head -c 1024 $(which "$1") | grep --quiet "PYTHON_ARGCOMPLETE_OK" 2>/dev/null; then
        local IFS=$(echo -e '\v')
        COMPREPLY=( $(IFS="$IFS" \
            COMP_LINE="$COMP_LINE" \
            COMP_POINT="$COMP_POINT" \
            _ARGCOMPLETE=1 \
            "$1" 8>&1 9>&2 1>/dev/null 2>/dev/null) )
        if [[ $? != 0 ]]; then
            unset COMPREPLY
        fi
    fi
}
complete -o nospace -o default -D -F _python_argcomplete_global
