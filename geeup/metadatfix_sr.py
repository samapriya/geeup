import csv
import time
import ee
import os
ee.Initialize()
with open(r'F:\CrossSensor\psrmeta.csv','r') as myfile:
    head=myfile.readlines()[0:1]
    delim=str(head).split(',')
    headlist=list(delim)
    root="users/samapriya/psrtest"
    list_req = {'id': root}
    children = ee.data.getList(list_req)
    
with open(r'F:\CrossSensor\psrmeta.csv', 'r') as f:
    reader = csv.DictReader(f,delimiter=",")
    num=1
    for i, line in enumerate(reader):
        absolute= ("earthengine asset set "
        +' -p '+'"'+"(string)"+headlist[1]+'='+line['platform']+'"'
        +' -p '+'"'+"(string)"+headlist[2]+'='+line['satType']+'"'+' -p '+'"'+"(string)"+headlist[3]+'='+line['satID']+'"'
        +' -p '+'"'+"(number)"+headlist[4]+'='+line['numBands']+'"'+' -p '+'"'+"(number)"+headlist[5]+'='+line['cloudcover']+'"'
        +' -p '+'"'+"(number)"+headlist[6]+'='+line['system:time_start']+'"'+' -p '+'"'+"(string)"+headlist[7]+'='+line['AtmModel']+'"'
        +' -p '+'"'+"(string)"+headlist[8]+'='+line['Aerosol_Model']+'"'+' -p '+'"'+"(string)"+headlist[9]+'='+line['AOT_Method']+'"'
        +' -p '+'"'+"(number)"+headlist[10]+'='+line['AOT_Std']+'"'+' -p '+'"'+"(number)"+headlist[11]+'='+line['AOT_Used']+'"'
        +' -p '+'"'+"(string)"+headlist[12]+'='+line['AOT_Status']+'"'+' -p '+'"'+"(number)"+headlist[13]+'='+line['AOT_MeanQual']+'"'
        +' -p '+'"'+"(number)"+headlist[14]+'='+line['LUTS_Version']+'"'+' -p '+'"'+"(number)"+headlist[15]+'='+line['SolarZenAngle']+'"'
        +' -p '+'"'+"(number)"+headlist[16]+'='+line['AOT_Coverage']+'"'+' -p '+'"'+"(string)"+headlist[17]+'='+line['AOT_Source']+'"'
        +' -p '+'"'+"(string)"+headlist[18]+'='+line['AtmCorr_Alg']+'"'+' -p '+'"'+"(number)"+headlist[19]+'='+line['incAngle']+'"'
        +' -p '+'"'+"(number)"+headlist[20]+'='+line['illAzAngle']+'"'+' -p '+'"'+"(number)"+headlist[21]+'='+line['illElvAngle']+'"'
        +' -p '+'"'+"(number)"+headlist[22]+'='+line['azAngle']+'"'+' -p '+'"'+"(number)"+'spcAngle'+'='+line['spcAngle']+'" '+root+'/'+line['id_no'])
        b=absolute
        try:
            if ee.data.getInfo(root+'/'+line['id_no']):
                os.system(absolute)
                print(str(len(children)-num)+" remaining of "+str(len(children)))
                num=num+1
            else:
                pass
        except Exception as e:
            print(e)
