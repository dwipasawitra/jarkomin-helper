#!/bin/bash
# Fixed from http://360percents.com/posts/bash-script-to-update-facebook-status-linux-mac-os-x/
#

email="fb-account"
pass="fb-password"
status="$2" #must be less than 420 chars

touch "cookie.txt" #create a temp. cookie file
loginpage=`curl -s -c ./cookie.txt -A "Mozilla/5.0" "https://m.facebook.com"` #initial cookies

#LOGIN PARAMETERS
form_action=`echo "$loginpage" | tr '"' "\n" | grep "https://m.facebook.com/login.php"`
form_data=`echo "$loginpage" | sed -e 's/.*<form//' | sed -e 's/form>.*//' | tr '/>' "\n" | grep 'input ' | grep -v "email\|pass"`

#FUNCTION PARSES FORM DATA LIKE HIDDEN INPUTS
function parse_form() {
    form_data="$1"
    params=""
        for (( i=1; i <= `echo "$form_data" | wc -l` ; i++ ))
            do
                name=`echo "$form_data" | sed -n "$i"p | tr ' ' "\n" | grep 'name' | cut -d '"' -f 2`
                value=`echo "$form_data" | sed -n "$i"p | tr ' ' "\n" | grep 'value' | cut -d '"' -f 2`
                params="$params$name=$value&"
            done
         echo "$params"
}

#LOGIN
params="email=$email&pass=$pass&"`parse_form "$form_data"`
logged_in=`curl -s -b ./cookie.txt -c ./cookie.txt -A "Mozilla/5.0" -d "$params" -L "$form_action"`
homepage=`curl -s -b ./cookie.txt -c ./cookie.txt -A "Mozilla/5.0" -L "https://m.facebook.com/groups/$1"`

#UPDATE STATUS
status_form=`echo "$homepage" | sed -e 's/.*<form id="composer_form//' | sed -e 's/textarea>.*//' | tr '/>' "\n" | grep 'input ' | grep 'name' | grep -v 'query' | grep -v 'status'`
status_action=`echo "$homepage" | tr '"' "\n" | grep "/a/group/"`
echo $status_action
status_params=`parse_form "$status_form"`"message=$status&update=Share"
update=`curl -s -b ./cookie.txt -c ./cookie.txt -A "Mozilla/5.0" -d "$status_params" -L "https://m.facebook.com$status_action"`
#$callback=`echo "$update" | grep "$status"` #just a primitive example of success checking

#LOGOUT
logout_link=`echo "$update" | tr '"' "\n" | grep "/logout.php?"`
logout=`curl -s -b ./cookie.txt -c ./cookie.txt -A "Mozilla/5.0" -L "https://m.facebook.com$logout_link"`

rm "cookie.txt" #remove cookie file
