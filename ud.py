import cx_Oracle
import PySimpleGUI as sg
from os import getcwd, startfile, mkdir
from paramiko import SSHClient, AutoAddPolicy
import threading

cwd = getcwd()

output = cwd + '/output/'
try:
    mkdir(output)
except:
    pass

templates = cwd + '/temp/'

PORT_SSH = 22
PORT_DB = 1521

USERS = {
    'QATAPP10': 
        {'Linux': ['qatapp101.unix.gsm1900.org', 'qatoln10', 'Amdocs21'],
        'DB':['qatdb101.unix.gsm1900.org', 'qatdb101', 'QATAPP10', 'QATAPP10'],
        'Path': '/tstuser/qatoln10/'
        },

    'SST01': 
        {'Linux': ['10.5.29.104', 'vstoln01', 'amdocs11'],
        'DB':['devdb101.unix.gsm1900.org', 'devdb101', 'SSTAPP01', 'SSTAPP01'],
        'Path': '/vstusr2/sst/gn/vstoln01/'
        },
    'SST02': 
        {'Linux': ['10.5.29.104', 'vstoln02', 'amdocs11'],
        'DB':['devdb101.unix.gsm1900.org', 'devdb101', 'SSTAPP02', 'SSTAPP02'],
        'Path': '/vstusr2/sst/gn/vstoln02/'
        },

    'SST03': 
        {'Linux': ['10.5.29.104', 'vstoln03', 'amdocs11'],
        'DB':['devdb101.unix.gsm1900.org', 'devdb101', 'SSTAPP03', 'SSTAPP03'],
        'Path': '/vstusr2/sst/gn/vstoln03/'
        },

    'SST13': 
        {'Linux': ['10.5.29.104', 'vstoln13', 'amdocs11'],
        'DB':['devdb101.unix.gsm1900.org', 'devdb101', 'SSTAPP13', 'SSTAPP13'],
        'Path': '/vstusr2/sst/csm/vstoln13/'
        },
    'QATAPP38': 
        {'Linux': ['qatapp201.unix.gsm1900.org', 'qatoln38', 'Amdocs21'],
        'DB':['qatdb201.unix.gsm1900.org', 'qatdb201', 'QATAPP38', 'QATAPP38'],
        'Path': '/tstuser/qatoln38/'
        }

}

cus_QAT, sftp, logical_date, conn_QAT, ssh, act = None, None, None, None, None, None
location = None

def connect_db_sftp(window):
    global cus_QAT, sftp, logical_date, conn_QAT, ssh, location
    
    # DB connection
    host_db = USERS[values['-HOST-']]['DB'][0]
    sid_db = USERS[values['-HOST-']]['DB'][1]
    user_db = USERS[values['-HOST-']]['DB'][2]
    pass_db = USERS[values['-HOST-']]['DB'][3]

    dsn_QAT = cx_Oracle.makedsn(host_db, PORT_DB, sid_db)
    conn_QAT = cx_Oracle.connect(user=user_db, password=pass_db, dsn=dsn_QAT)
    cus_QAT = conn_QAT.cursor()

    # SFTP connection
    host_ssh = USERS[values['-HOST-']]['Linux'][0]
    user_ssh = USERS[values['-HOST-']]['Linux'][1]
    pass_ssh = USERS[values['-HOST-']]['Linux'][2]

    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(host_ssh, PORT_SSH, user_ssh, pass_ssh)

    sftp = ssh.open_sftp()
    
    logical_date = cus_QAT.execute('select LOGICAL_DATE from logical_date')
    logical_date = logical_date.fetchone()
    logical_date = logical_date[0].strftime('%Y%m%d')

    location = USERS[values['-HOST-']]['Path']
    window.write_event_value('-THREAD_DONE-', 'Long operation done!')
    

def custom_replace(section, index, replace_value):
    section[index] = section[index].replace(section[index].split('\t')[1], replace_value)
    return section

def edit_section_1(section, ban, sim, l_d):
    section = custom_replace(section, 5, ban+'\n')
    section = custom_replace(section, 11, sim+'\n')
    section = custom_replace(section, 13, sim+'\n')
    section = custom_replace(section, 10, l_d+'\n')
    
    return section

def edit_section_2(section, sim, values, l_d):
    section_2_new = {}
    for i in range(int(sim)):
        sec2 = section.copy()
        sec2 = custom_replace(sec2, 0, str(i+1)+'\n')
        sec2 = custom_replace(sec2, 7, str(values[i])+'\n')
        sec2 = custom_replace(sec2, 11, l_d+'\n')
        sec2 = custom_replace(sec2, 34, l_d+'\n')
        section_2_new[f'copy_{i}'] = sec2
    
    new_section2 = []
    for v in section_2_new.values():
        for x in v:
            new_section2.append(x)
    
    return new_section2

def edit_section_4(section, sim, l_d):
    section_4_new = {}
    for i in range(int(sim)):
        sec4 = section.copy()
        sec4 = custom_replace(sec4, 0, str(i+1)+'\n')
        sec4 = custom_replace(sec4, 1, values['-SOC-']+'\n')
        sec4 = custom_replace(sec4, 2, l_d+'\n')
        sec4 = custom_replace(sec4, 3, values['-PTYPE-'])
        section_4_new[f'copy_{i}'] = sec4

    new_section4 = []
    for v in section_4_new.values():
        for x in v:
            new_section4.append(x)

    return new_section4

def get_sims(sim):
    value = cus_QAT.execute(f'''select SERIAL_NUMBER from serial_item_inv where resource_status='AA' and equ_type ='S' and service_partner_Id in ('TMO','ALL') and sim_expiration_date is null and rownum <= {sim} ''')
    return [x[0] for x in value]

def create_new_file(ban, sim, logical_date):
    with open(f'{templates}evCrVarActOrd_template_activate.ud', 'r') as file:
                data = file.readlines()

    section1 = data[:14]
    section2 = data[14:53]
    section3 = data[53:54]
    section4 = data[54:59]
    section5 = data[59:]

    section1 = edit_section_1(section1, ban, sim, logical_date)
    section2 = edit_section_2(section2, sim, sim_values, logical_date)
    section3 = custom_replace(section3, 0, sim+'\n')
    section4 = edit_section_4(section4, sim, logical_date)

    new_ud_file = section1 + section2 + section3 + section4 + section5

    with open(f'{output}evCrVarActOrd_{ban}.ud', 'w', newline='\n') as f:
        f.writelines(new_ud_file)

def upload_file():
    global location
    loc = location
    try:
        loc += values['-LOC-'] + '/'
        sftp.put(f'{output}evCrVarActOrd_{ban}.ud',
                f'{loc}evCrVarActOrd_{ban}.ud')
    except:
        ssh.exec_command(f"cd {location}; mkdir {values['-LOC-']}")
        sftp.put(f'{output}evCrVarActOrd_{ban}.ud',
                f'{loc}evCrVarActOrd_{ban}.ud')

def upload_file_csr():
    global location
    loc = location
    try:
        loc += values['-LOC-'] + '/'

        sftp.put(f"{output}csSvBulkAct00_{act}_{values['-BAN_MORE-']}.ud",
                f"{loc}csSvBulkAct00_{act}_{values['-BAN_MORE-']}.ud")
    except:
        ssh.exec_command(f"cd {location}; mkdir {values['-LOC-']}")
        sftp.put(f"{output}csSvBulkAct00_{act}_{values['-BAN_MORE-']}.ud",
                f"{loc}csSvBulkAct00_{act}_{values['-BAN_MORE-']}.ud")

def validate_count(v): # Changed function name from cancel_count to validate_count 
    split_list = v['-SUB_LIST-'].replace(' ', '').split()
    if int(v['-SUB_COUNT-']) < len(split_list):
        sg.PopupError("Subscriber count is less than subscriber")
        return False
    elif int(v['-SUB_COUNT-']) > len(split_list):
        sg.PopupError("Subscriber count is more than subscriber")
        return False
    else:
        return True

def create_csr_file(ud_list, mapping):
    global act
    with open(f'{templates}csSvBulkAct00_template_csr.ud', 'r') as file:
                data = file.readlines()

    section1 = data[:14]
    section2 = data[14:]

    section1 = custom_replace(section1, 5, values['-BAN_MORE-']+'\n')
    section1 = custom_replace(section1, 8, logical_date+'\n')
    section1 = custom_replace(section1, 9, values['-PDATE-']+'000000\n')
    act, rdate = ('SUS', values['-RDATE-']) if values['-ACT-'] == 'Suspend' else ('CAN', None) if values['-ACT-'] == 'Cancel' else ('RSP', None)
    section1 = custom_replace(section1, 10, act+'\n')
    section1 = custom_replace(section1, 11, values['-RCODE-']+'\n')
    section1 = custom_replace(section1, 13, str(len(ud_list))+'\n')

    if rdate:
        section1.insert(12, 'CBR_DT_P1\t'+rdate+'000000\n')

    sec_2_new = []
    sec2 = section2.copy()
    for i in range(len(ud_list)):
        sec2 = custom_replace(section2, 0, ud_list[i]+'\n')
        sec2 = custom_replace(section2, 1, mapping[ud_list[i]]+'\n')
        sec_2_new.extend(sec2.copy())

    with open(f"{output}csSvBulkAct00_{act}_{values['-BAN_MORE-']}.ud", 'w', newline='\n') as f:
        f.writelines(section1+sec_2_new+['\n'])

def ban_sub_validation():
    ud_list = []
    non_ud_list = []
    proceed = 'Yes'

    cus_QAT.execute(f'select CUSTOMER_ID from subscriber where CUSTOMER_ID={values["-BAN_MORE-"]}')
    ban_exist = cus_QAT.fetchone()
    if ban_exist:
        subscribers = values['-SUB_LIST-'].split()
        mapping = {}

        if values["-ACT-"] == "Restore":
            status = ('S',)
        elif values["-ACT-"] == "Cancel":
            status = ('A', 'S')
        else:
            status = ('A',)

        cus_QAT.execute(f'select SUBSCRIBER_NO, CUSTOMER_ID, PRODUCT_TYPE, SUB_STATUS FROM subscriber where CUSTOMER_ID={values["-BAN_MORE-"]} and subscriber_no in {*subscribers,}')

        rows = cus_QAT.fetchall()

        row_set = set()
        sub_set = set(subscribers)

        if len(rows) != int(values['-SUB_COUNT-']):
            for row in rows:
                row_set.add(row[0])
            diff = len(sub_set.difference(row_set))
            
            if diff == 4:
                sg.PopupError("No subscribers exist for inserted ban!\nPlease re-enter the values.")
                return
            else:
                proceed = sg.PopupYesNo(f"{*sub_set.difference(row_set),}\nThese subscribers not found!\nDo you want to proceed?")
        if proceed == 'No':
            return
        else:
            for row in rows:
                mapping[row[0]] = row[2]
                if row[-1] not in status:
                    a1 = sg.PopupYesNo(f"{row[0]} is not in correct status. Do you want to add this subscriber to UD file?")
                    if a1 == 'Yes':
                        ud_list.append(row[0])
                    else:
                        non_ud_list.append(row[0])
                else:
                    ud_list.append(row[0])
            

            if non_ud_list and ud_list:
                a2 = sg.PopupYesNo(f"{len(non_ud_list)} subscribers didn't match the expected status!\nClick 'Yes' to proceed with UD creation of the remaining subscribers.\nClick 'No' to re-enter subscribers.")
                if a2 == 'Yes':
                    create_csr_file(ud_list, mapping)
                    upload = sg.PopupYesNo(f"Created UD file with {len(ud_list)} sub(s).\nDo you want to upload the file?")
                    if upload == 'Yes':
                        upload_file_csr()
                        sg.PopupOK('File Uploaded')
                else:
                    return
            elif not ud_list:
                sg.PopupOK("No files created.")
                return
            else:
                create_csr_file(ud_list, mapping)
                upload = sg.PopupYesNo(f"Created UD file with {len(ud_list)} sub(s).\nDo you want to upload the file?")
                if upload == 'Yes':
                    upload_file_csr()
                    sg.PopupOK('File Uploaded')
    else:
        sg.PopupError("Ban does not exist!")
        return

layout_home = [
    [sg.Text('Select Host', size=(14, 1)),
     sg.DropDown(list(USERS.keys()), key='-HOST-', size=(20, 1), enable_events=True, readonly=True)],

    [sg.Text("Select Activity",size=(15,1))],
    [sg.Radio('Activate', key='-ACTIVATE-', size=(10,1), group_id='activity', default=True), sg.Radio('Cancel/Suspend/Restore', key="-OTHERS-", size=(20,1), group_id='activity')],

    [sg.Text('Target Folder Name', size=(15, 1)),
     sg.Input('', key='-LOC-', size=(10, 1))],

    [sg.Button('Go!', key='-SUBMIT_ACTIVITY-'), sg.Button('Exit', key='-EXIT-')]
]

layout_activate = [
    [sg.Text('BAN', size=(15, 1)),
     sg.Input('', key='-BAN_ACTIVATE-', size=(20, 1), enable_events=True)],
     
    [sg.Text('Price Plan/SOC', size=(15, 1)),
     sg.Input('', key='-SOC-', size=(20, 1))],

    [sg.Text('Product Type', size=(15, 1)),
     sg.DropDown(['B', 'I', 'P'], key='-PTYPE-', size=(8, 1))],

    [sg.Text('Number of SIMs', size=(15, 1)),
     sg.Input('', key='-SIM-', size=(10, 1), enable_events=True)],

    [sg.Button('Go!', key='-SUBMIT_ACTIVATE-'), sg.Button('Back', key='-BACK_ACTIVATE-'), sg.Button('Exit', key='-EXIT_ACTIVATE-')]
]

activity = ["Cancel","Restore","Suspend"]

layout_more = [
    [sg.Text('BAN', size=(20, 1)),
     sg.Input('', key='-BAN_MORE-', size=(20, 1), enable_events=True)],

    [sg.Text('Number of Subscribers', size=(20, 1)),
    sg.Input('', key='-SUB_COUNT-', size=(20, 1), enable_events=True)],

    [sg.Text('Subscriber:Product Type', size=(20, 4)),
    sg.Multiline('', key='-SUB_LIST-', size=(18, 5))],

    [sg.Text('Select Activity', size=(20,1)),
    sg.DropDown(activity, key='-ACT-', size=(19, 1), enable_events=True, readonly=True)],

    [sg.Text('Reason Code', size=(20 ,1)),
    sg.Input('', key='-RCODE-', size=(20, 1))],

    [sg.Text('Process Date\nFormat (yyyymmdd)', size=(20, 2)),
    sg.Input('', key='-PDATE-', size=(20,1), enable_events=True)],

    [sg.Text('Restore Date (Optional)', size=(20, 1)),
    sg.Input('', key='-RDATE-', size=(20,1), disabled=True, disabled_readonly_background_color='gray', enable_events=True)],

    [sg.Button('Go!', key='-SUBMIT_MORE-'), sg.Button('Back', key='-BACK_MORE-'), sg.Button('Exit', key='-EXIT_MORE-')]
]

main_layout = [
    [sg.Column(layout_home, visible=True, key='-COL1-'),

    sg.Column(layout_activate, visible=False, key='-COL2-'),

    sg.Column(layout_more, visible=False, key='-COL3-')]
]

window = sg.Window('UD File', main_layout)

thread = timeout = None

image = b"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"

while True:
    event, values = window.read(timeout=timeout)
    
    if event in (sg.WIN_CLOSED, '-EXIT-', '-EXIT_ACTIVATE-', '-EXIT_MORE-'):
        break
    
    if event in ('-BACK_ACTIVATE-', '-BACK_MORE-'):
        window['-COL1-'].update(visible=True)
        window['-COL2-'].update(visible=False)
        window['-COL3-'].update(visible=False)

    if event == '-ACT-':
        if values['-ACT-'] == 'Suspend':
            window['-RDATE-'].update(disabled=False)
        else:
            window['-RDATE-'].update(disabled=True)

    if event == '-SUBMIT_ACTIVITY-':
        if values['-HOST-'] and values['-LOC-']:
            if values['-ACTIVATE-']:
                window['-COL2-'].update(visible=True)
                window['-COL1-'].update(visible=False)
            else:
                window['-COL3-'].update(visible=True)
                window['-COL1-'].update(visible=False)
        else:
            sg.PopupError('Please select all values!')

    if event == "-SUBMIT_MORE-":
        if all([values['-BAN_MORE-'], values["-SUB_COUNT-"], values['-SUB_LIST-'], values['-ACT-'], values['-RCODE-'], values['-PDATE-']]):
            if validate_count(values): # Changed function name from cancel_count to validate_count 
                ban_sub_validation()
        else:
            sg.popup_error("Enter all values!")

    if event == '-HOST-' and not thread:
        window['-SUBMIT_ACTIVITY-'].update(disabled=True)
        window['-EXIT-'].update(disabled=True)
        timeout = 30
        try:
            thread = threading.Thread(target=connect_db_sftp, args=(window,), daemon=True)
            thread.start()
        except Exception as e:
            print(e)
            sg.PopupError('Please connect to VPN or check your network connection!')
            window['-HOST-'].update('')

    if event == '__TIMEOUT__':
        sg.popup_animated(image, background_color='white', transparent_color='white', time_between_frames=30)
        
    if event == '-THREAD_DONE-':
        window['-SUBMIT_ACTIVITY-'].update(disabled=False)
        window['-EXIT-'].update(disabled=False)
        thread = timeout = None
        sg.popup_animated(None)
        sg.PopupOK("Connected!")

    if len(values['-BAN_ACTIVATE-']) and values['-BAN_ACTIVATE-'][-1] not in ('0123456789'):
        window['-BAN_ACTIVATE-'].update(values['-BAN_ACTIVATE-'][:-1])

    if len(values['-BAN_ACTIVATE-']) > 9:
        window['-BAN_ACTIVATE-'].update(values['-BAN_ACTIVATE-'][:9])
        
    if len(values['-SIM-']) and values['-SIM-'][-1] not in ('0123456789'):
        window['-SIM-'].update(values['-SIM-'][:-1])

    if len(values['-SIM-']) > 3:
        window['-SIM-'].update(values['-SIM-'][:3])

    if len(values['-BAN_MORE-']) and values['-BAN_MORE-'][-1] not in ('0123456789'):
        window['-BAN_MORE-'].update(values['-BAN_MORE-'][:-1])

    if len(values['-BAN_MORE-']) > 9:
        window['-BAN_MORE-'].update(values['-BAN_MORE-'][:9])
        
    if len(values['-SUB_COUNT-']) and values['-SUB_COUNT-'][-1] not in ('0123456789'):
        window['-SUB_COUNT-'].update(values['-SUB_COUNT-'][:-1])

    if len(values['-SUB_COUNT-']) > 2:
        window['-SUB_COUNT-'].update(values['-SUB_COUNT-'][:2])

    if len(values['-PDATE-']) and values['-PDATE-'][-1] not in ('0123456789'):
        window['-PDATE-'].update(values['-PDATE-'][:-1])

    if len(values['-PDATE-']) > 8:
        window['-PDATE-'].update(values['-PDATE-'][:8])
    
    if len(values['-RDATE-']) and values['-RDATE-'][-1] not in ('0123456789'):
        window['-RDATE-'].update(values['-RDATE-'][:-1])

    if len(values['-RDATE-']) > 8:
        window['-RDATE-'].update(values['-RDATE-'][:8])
        
    if event == '-SUBMIT_ACTIVATE-':
        if all((values['-BAN_ACTIVATE-'], values['-SIM-'], values['-PTYPE-'], values['-SOC-'])):

            ban = values['-BAN_ACTIVATE-']
            sim = values['-SIM-']
            
            sim_values = get_sims(sim)
            create_new_file(ban, sim, logical_date)
            
            open_folder = sg.PopupYesNo('UD File created\n\nDo you want to open the folder?', modal=True)
            if open_folder == 'Yes':
                startfile(output)
            
            upload = sg.PopupYesNo('Upload file to server?', modal=True)
            if upload == 'Yes':
                upload_file()
                sg.PopupOK('File Uploaded')
        else:
            sg.PopupError('Enter all values', modal=True)

if conn_QAT:
    conn_QAT.close()
    ssh.close()
    sftp.close()

window.close()

