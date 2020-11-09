#!/bin/bash

inform()
{
    local msg=${1}
    echo "mask_password.sh: ${msg}"
}

get_options()
{
    local arguments=($@)

    unset g_password
    unset g_file
    g_verbose="FALSE"

    # parse arguments
    local num_args=${#arguments[@]}
    local argument
    local index=0

    while [ ${index} -lt ${num_args} ]; do
        argument=${arguments[index]}

        case ${argument} in
            --password=*)
                g_password=${argument/*=/""}
                index=$(( index + 1 ))
                ;;
            --file=*)
                g_file=${argument/*=/""}
                index=$(( index + 1 ))
                ;;
            --verbose)
                g_verbose="TRUE"
                index=$(( index + 1 ))
                ;;
            --quiet)
                g_verbose="FALSE"
                index=$(( index + 1 ))
                ;;
            *)
                inform "ERROR: unrecognized option: ${argument}"
                exit 1
                ;;
        esac
    done

    if [ -z "${g_password}" ]; then
        inform "ERROR: password to mask (--password=) required"
        exit 1
    fi

    if [ -z "${g_file}" ]; then
        inform "ERROR: file to mask password in (--file=) required"
        exit 1
    fi
}

verbose_inform()
{
    local msg=${1}
    if [ "${g_verbose}" = "TRUE" ] ; then
        inform "${msg}"
    fi
}

main()
{
    get_options "$@"

    # if file exists as a "regular" file: not a directory or device file
    if [ -f "${g_file}" ]; then

        local found
        found=$(grep ${g_password} ${g_file})

        if [ ! -z "${found}" ] ; then
            verbose_inform "Masking password in file: ${g_file}"
            sed 's/'${g_password}'/\*\*\*password_mask\*\*\*/' ${g_file} > ${g_file}.password_masked
            mv ${g_file}.password_masked ${g_file}
            verbose_inform "Masked password in file: ${g_file}"
        fi

    fi
}

# Invoke the main function to get things started
main "$@"
