#!/usr/bin/env bash

#this bash shell is written by the `lazyinfo()` function.

url="http://localhost:8000/db/security/roles"
scriptname=tests/test_urls_security_psroledefn.py
linenum=874
funcname=test_it
editor='/Applications/Sublime Text.app/Contents/SharedSupport/bin/subl'
candiff=1
fnp_got="/RAMDisk/lazy/got/test_urls_security_psroledefn/test_urls_security_psroledefn.Test_List.test_it.html"
fnp_exp="/lazy/exp/test_urls_security_psroledefn/test_urls_security_psroledefn.Test_List.test_it.html"
message=""



if [ ! -z "$message" ]; then
    echo '********************************'
    echo '* '"$message"' *'
    echo '********************************'
fi


if [ ! -z "$scriptname" ]; then
    echo "$scriptname $funcname @ line $linenum"
fi


if [[ "$@" == "-h" ]]
then



    echo "difflast -cp to copy got to exp which resets expectations"

    if [ ! -z "$candiff" ]; then
        echo "difflast -diff to use diff"
    fi

    echo "difflast -exp to open fnp_exp" 
    echo "difflast -got to open fnp_got" 
    echo "difflast -rmgot to rm fnp_got" 
    echo "difflast -path to show paths" 

    if [ ! -z "$scriptname" ]; then
        echo "difflast -edit to open $scriptname at line $linenum with $editor" 
    fi


    if [ ! -z "$url" ]; then
        echo "difflast -url to open the url" 
    fi

    exit
fi

if [ ! -z "$scriptname" ]; then
    if [[ "$1" == "-edit" ]]; then
        "$editor" $scriptname:$linenum
        exit
    fi
fi

if [ ! -z "$url" ]; then
    if [[ "$1" == "-url" ]]; then
        #attempt to open in your browswer
        open "$url"
        exit
    fi
fi

if [ ! -z "$candiff" ]; then

    if [[ "$1" == "-diff" ]]; then
            diff $fnp_exp $fnp_got
            exit
    fi

fi

if [[ "$1" == "-path" ]]; then
        echo "$fnp_exp"
        echo "$fnp_got"
        exit
fi

if [[ "$1" == "-exp" ]]; then
        "$editor" $fnp_exp
        exit
fi

if [[ "$1" == "-rmgot" ]]; then
        rm $fnp_got
        exit
fi

if [[ "$1" == "-got" ]]; then
        "$editor" $fnp_got
fi

if [[ "$1" == "-cp" ]]; then
    echo "this would copy"
    echo "cp "
    echo "$fnp_got"
    echo " to"
    echo "$fnp_exp"

    read -p "Are you sure? " -n 1 -r
    echo    # (optional) move to a new line
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        cp $fnp_exp
    else
        ksdiff $fnp_got
    fi


else
    ksdiff $fnp_exp $fnp_got
fi


