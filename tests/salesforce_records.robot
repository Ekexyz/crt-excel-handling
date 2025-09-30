*** Settings ***
Resource                ../resources/common.resource
Resource                ../resources/excel.resource
Test Teardown           Close All Excel Documents
Suite Setup             Setup Browser
Suite Teardown          End Suite


*** Test Cases ***
Create Accounts from Excel Data
    [Documentation]     Read Salesfoce record data from excel and create accounts.
    [Tags]              excel    data    salesforce    account    create
    Login

    ${file}=            Set Variable    ${CURDIR}/../files/salesforce_test_data.xlsx
    ${sheet_name}=      Set Variable    Accounts

    # Use Read Excel Data from excel.resource file to read all rows to a list of dictionaries
    @{accounts_list}=   Read Excel Data      ${file}    ${sheet_name}

    @{account_links}=   Create List

    FOR    ${account}    IN    @{accounts_list}
        ClickItem           Accounts    tag=a    delay=2
        VerifyText          Recently Viewed    anchor=Accounts

        ClickUntil          Account Information    New    anchor=Import
        UseModal            On

        TypeText            *Account Name    ${account}[account_name]    delay=1
        TypeText            Phone    ${account}[phone]    anchor=Fax    delay=1
        TypeText            Fax    ${account}[fax]    anchor=Phone    delay=1
        TypeText            Website    ${account}[website]    delay=1

        PickList            Type    ${account}[type]
        PickList            Industry    ${account}[industry]
        TypeText            Employees    ${account}[employees]    delay=1
        TypeText            Annual Revenue    ${account}[annual_revenue]    delay=1

        ClickText           Save    partial_match=False    delay=1
        UseModal            Off
        VerifyText          was created.    timeout=45

        VerifyText          ${account}[account_name]    anchor=Account

        ${account_url}=     GetUrl
        Append To List      ${account_links}    ${account_url}
    END
    
    Set Suite Variable  ${account_links}

Update Account
    [Documentation]     Read Salesfoce record data from excel and update an existing account.
    [Tags]              excel    data    salesforce    account    update

    ${file}=            Set Variable    ${CURDIR}/../files/salesforce_test_data.xlsx
    ${sheet_name}=      Set Variable    Accounts
    ${identifier}=      Set Variable    Partner, Inc.

    # Use Read Excel Row to Variables from excel.resource file to create suite variables from row values
    Read Excel Row to Variables    ${file}    ${sheet_name}    ${identifier}

    # Check that the newly created variables exist
    Log To Console      ${account_name}
    Log To Console      ${phone}
    Log To Console      ${fax}
    Log To Console      ${website}
    Log To Console      ${type}
    Log To Console      ${industry}
    Log To Console      ${employees}
    Log To Console      ${annual_revenue}

    ClickItem           Accounts    tag=a    delay=2
    ClickText           Search...    delay=1
    TypeText            Search Accounts and more    ${account_name}    delay=1
    ClickItem           ${account_name}    tag=span    delay=2

    VerifyText          ${account_name}    anchor=Account
    ClickUntil          Edit ${account_name}    Edit    anchor=Change Owner
    UseModal            On

    ${new_phone}=       Set Variable    (123) 555-1234
    TypeText            Phone    ${new_phone}    anchor=Fax

    ClickText           Save    partial_match=False    delay=1
    UseModal            Off
    VerifyText          was saved.    timeout=45

    ClickText           Details
    VerifyField         Account Name    ${account_name}
    VerifyField         Phone    ${new_phone}
    VerifyField         Website    ${website}

    ClickItem           Accounts    tag=a    delay=2
    VerifyText          Recently Viewed

Delete Created Accounts
    [Tags]              excel    data    salesforce    account    delete
    FOR    ${account_url}    IN    @{account_links}
        GoTo                ${account_url}
        ClickItem           Delete    tag=button    delay=1
        VerifyText          Are you sure you want to delete this account?
        ClickText           Delete    anchor=Cancel
        VerifyText          was deleted.
    END
