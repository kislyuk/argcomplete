# bash completion for python distutils setup.py

have python &&
_setup_py()
{
    if [ "${COMP_WORDS[0]}" == "python" ]; then
        if [ "${COMP_WORDS[1]}" != "setup.py" ]; then
            type _python &> /dev/null && _python $COMP_WORDS
            return 0
        else
            unset COMP_WORDS[0]
            unset COMP_WORDS[0]
            COMP_WORDS=("python setup.py"  "${COMP_WORDS[@]}")
        fi
    fi
    local cur prev helpopts commands
    _get_comp_words_by_ref cur prev 
    helpopts=$(_parse_help "${COMP_WORDS[0]}")
    commands=$(${COMP_WORDS[0]} --help-commands | awk /^[[:space:]]{2}/'{if ($1!="or:")print $1}')
    if [ -n "${COMP_WORDS[1]}" ] && echo "${commands}"|grep -qw "${COMP_WORDS[1]}"; then
        COMPREPLY=($(compgen -W "$(_parse_help "${COMP_WORDS[0]} ${COMP_WORDS[1]}")" -- "$cur"))
        return 0
    fi
    COMPREPLY=($(compgen -W "$helpopts $commands" -- "$cur"))
    return 0
} &&
complete -F _setup_py setup.py ./setup.py python

# Local variables:
# mode: shell-script
# sh-basic-offset: 4
# sh-indent-comment: t
# indent-tabs-mode: nil
# End:
# ex: ts=4 sw=4 et filetype=sh
