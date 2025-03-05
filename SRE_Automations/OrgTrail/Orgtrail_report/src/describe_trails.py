'''
Author: Novartis
Contributors: Rohan T
Date: 28-06-2023 (Initial Version)

The below code is to describe all trails of the account
'''

class describetrails:


    def trail_describe(self,LOGGER,client,region_name):
        finaltrails=[]
        try:
            response = client.describe_trails()
            trailname=[]
            for i in response['trailList']:
                trailname.append(i['Name'])
            LOGGER.info(trailname)

            for trail in trailname:
                try:
                    response = client.get_trail(Name=trail)
                    for i in response['Trail']:               #For multi region trails, we want to print only once in the home region
                        if response['Trail']['HomeRegion']==region_name:
                            finaltrails.append(trail)
                            break
                except:
                    continue

            
            LOGGER.info(finaltrails)

        except Exception as e:
            LOGGER.info(e)
        
        return finaltrails
