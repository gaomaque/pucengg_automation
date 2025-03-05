'''
Author: Novartis
Contributors: Rohan T
Date: 28-06-2023 (Initial Version)

The below code is to describe all trails of the account except the organziation trail
'''

class describelogging:


    def trail_logging(self,LOGGER,client,trailname):
        final_trails=[]
        final_status=[]
        try:
            for trail in trailname:
                if trail not in ["NVSGISMST-ORGCLOUDTRAIL","NVSGISMSTCN-ORGCLOUDTRAIL"]:
                    logging_status = client.get_trail_status(Name=trail)
                    status = logging_status['IsLogging']
                    final_status.append(status)
                    final_trails.append(trail)
            
            LOGGER.info("All trails except organization trail are {}".format(final_trails))

        except Exception as e:
            LOGGER.info(e)
        return final_status,final_trails
