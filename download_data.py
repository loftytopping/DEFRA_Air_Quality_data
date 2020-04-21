##########################################################################################
#                                                                                        #
#    Scripts to to download AURN air quality data from uk-air.defra.gov.uk               #
#    Also includes ability to plot diurnal profile comparisons                           #
#                                                                                        #
#    This is free software: you can redistribute it and/or modify it under               #
#    the terms of the GNU General Public License as published by the Free Software       #
#    Foundation, either version 3 of the License, or (at your option) any later          #
#    version.                                                                            #
#                                                                                        #
#    This is distributed in the hope that it will be useful, but WITHOUT                 #
#    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS       #
#    FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more              #
#    details.                                                                            #
#                                                                                        #
#    You should have received a copy of the GNU General Public License along with        #
#    this repository.  If not, see <http://www.gnu.org/licenses/>.                       #
#                                                                                        #
##########################################################################################
# 2020, author David Topping: david.topping@manchester.ac.uk

# File to download AURN air quality data from uk-air.defra.gov.uk
# Converts R files into Pandas dataframes

import pyreadr
import os.path
import os
import requests
import pdb
import wget
import pandas as pd
import numpy as np
import datetime
import sys
from pathlib import Path
import seaborn as sns
import matplotlib.pyplot as plt

# First check to see if data directory exists. If not, create it
# Change thee download path according to your needs
# Check if it exists. If not, create it
download_path = "/AURN_data_download"
Path(download_path).mkdir(parents=True, exist_ok=True)

# The download URLs from the DEFRA website
meta_data_url = "https://uk-air.defra.gov.uk/openair/R_data/AURN_metadata.RData"
data_url = "https://uk-air.defra.gov.uk/openair/R_data/"

# Does the metadatafile exist? This includes information about all of the Sites
# captured in the AURN database
meata_data_filename = 'AURN_metadata.RData'
# Check to see if this exists in your
if os.path.isfile(meata_data_filename) is True:
    print("Meta data file already exists in this directory, will use this")
else:
    print("Downloading Meta data file")
    wget.download(meta_data_url)

# Read the RData file into a Pandas dataframe
metadata = pyreadr.read_r(meata_data_filename)

# The commented lines below will allow you to see what is listed in the
# metadata file
# let's see what we got
#print("Metadata keys are:", metadata['AURN_metadata'].keys())

# Shall we list the unique entries for local authority?
#print("Agglomeration entries are: ",metadata['AURN_metadata'].local_authority.unique() )

# Now lets show the station entries [site_names] for, say, Manchester
# We will cycle through each entry in turn later to download the entire dataset
#subset_df = metadata['AURN_metadata'][metadata['AURN_metadata'].local_authority == 'Manchester']
#print("List of stations in chosen authority", subset_df.site_name.unique())

# In the following we now download the data. Here we have a number of options
# - Specify the years to download data for
# - Specify the local authority[ies] to download data for
# - Download data for all authorities

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------

# In every case we need to specify a year or years to download as a list
years = [2016,2017,2018,2019,2020]
# If a single year is passed then convert to a list with a single value
if type(years) is int:
    years = [years]
current_year = datetime.datetime.now().year
years = sorted(years)

# List authorities manually, or fit to all?
manual_selection = False #This means we need to list our authorities.
                        # If in doubt, please check the name of the list_authorities in the metadata file above
                        # We again use a list of authorities as set out below
save_to_csv = False # We Concatenate dataframes into one file. If you would like to save this to a csv file, set to True

# I also provide the ability to plot diurnal comparions for O3, NO2, Ox, PM2.5 and PM10 where available
plot_diurnal_comparison = True

site_data_dict=dict()
site_data_dict_name=dict()
if manual_selection is True:
    list_authorities = ['Manchester','Salford','Newcastle upon Tyne']
else:
    #pdb.set_trace()
    list_authorities = metadata['AURN_metadata'].local_authority.unique().tolist()

if plot_diurnal_comparison is True:
    site_data_dict=dict()
    site_data_dict_name=dict()


# Now cycle through each authority and thus each site within
for local_authority in list_authorities:

    # Does the authority data folder already exist? If not, create it
    data_path = download_path+"/"+local_authority+"/"
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    # Here we use the information on the metadata file to look at times, parameters etc
    subset_df = metadata['AURN_metadata'][metadata['AURN_metadata'].local_authority == local_authority]

    # Check to see if your requested years will work and if not, change it
    # to do this lets create two new columns of datetimes for earliest and latest
    # This does not guarantee all parameters are available for all years
    datetime_start=pd.to_datetime(subset_df['start_date'].values, format='%Y/%m/%d').year
    #Problem with the end date is it could be ongoing. In which case, convert that entry into a date and to_datetime
    now = datetime.datetime.now()
    datetime_end_temp=subset_df['end_date'].values
    step=0
    for i in datetime_end_temp:
        if i == 'ongoing':
            datetime_end_temp[step]=str(now.year)+'-'+str(now.month)+'-'+str(now.day)
        step+=1
    datetime_end = pd.to_datetime(datetime_end_temp).year

    earliest_year = np.min(datetime_start)
    latest_year = np.max(datetime_end)

    # Need to check valid year range
    proceed = True

    if latest_year < np.min(years):
        print("Invalid end year, out of range for ", local_authority)
        proceed = False
    if earliest_year > np.max(years):
        print("Invalid start year, out of range for ", local_authority)
        proceed = False
    ## Check year range now requested
    # If we find we have requested an invalid date range then create a neew list of years
    years_temp = years

    try:
        if np.min(years) < earliest_year:
            print("Invalid start year. The earliest you can select for ", local_authority ," is ", earliest_year)
            years_temp = years_temp[np.where(np.array(years_temp)==earliest_year)[0][0]::]
            #sys.exit()
        if np.max(years) > latest_year:
            print("Invalid end year. The latest you can select for ", local_authority ," is ", latest_year)
            years_temp = years_temp[0:np.where(np.array(years_temp)==latest_year)[0][0]]
    except:
        print("No valid year range")
        proceed = False
        #sys.exit()

    # Create dictionary of all site data from entire download session
    # This removes any rows with NaNs
    clean_site_data=True

    ################################################################################
    # Cycle through all sites in the local local_authority

    if proceed is True:

        for site in subset_df['site_id'].unique():

            site_type = metadata['AURN_metadata'][metadata['AURN_metadata'].site_id == site]['location_type'].unique()[0]

            # Do we want to check if the site has 'all' of the pollutants?
            #if check_all is True:
            #    if all(elem in ['O3', 'NO2', 'NO', 'PM2.5', 'temp', 'ws', 'wd'] for elem in metadata['AURN_metadata'][metadata['AURN_metadata'].site_id == site]['parameter'].values)
            station_name = metadata['AURN_metadata'][metadata['AURN_metadata'].site_id == site]['site_name'].values[0]
            # Create a list of dataframes per each yearly downloaded_data
            # Concatenate these at the end
            downloaded_site_data = []

            for year in years_temp:
                #pdb.set_trace()
                try:
                    download_url = "https://uk-air.defra.gov.uk/openair/R_data/"+site+"_"+str(year)+".RData"
                    downloaded_file=site+"_"+str(year)+".RData"

                    # Check to see if file exists or not. Special case for current year as updates on hourly basis
                    filename_path = download_path+"/"+local_authority+"/"+downloaded_file

                    #pdb.set_trace()
                    if os.path.isfile(filename_path) is True and year != current_year:
                        print("Data file already exists", station_name ," in ",str(year))
                    else:
                        if os.path.isfile(filename_path) is True and year == current_year:
                            # Remove downloaded .Rdata file [make this optional]
                            os.remove(filename_path)
                            print("Updating file for ", station_name ," in ",str(year))
                        print("Downloading data file for ", station_name ," in ",str(year))
                        wget.download(download_url,out=download_path+"/"+local_authority+"/")

                    # Read the RData file into a Pandas dataframe
                    downloaded_data = pyreadr.read_r(filename_path)
                    # Add coordinates as reference data [will change this to be not entire column]
                    downloaded_data[site+"_"+str(year)]['latitude']=metadata['AURN_metadata'][metadata['AURN_metadata'].site_id == site].latitude.values[0]
                    downloaded_data[site+"_"+str(year)]['longitude']=metadata['AURN_metadata'][metadata['AURN_metadata'].site_id == site].longitude.values[0]

                    # Append to dataframe list
                    downloaded_site_data.append(downloaded_data[site+"_"+str(year)])

                except:
                    print("Couldnt download data from ", year, " for ", station_name)

            if len(downloaded_site_data) == 0:
                print("No data could be downloaded for ", station_name)
            #final_dataframe = pd.DataFrame()
            else:
                final_dataframe = pd.concat(downloaded_site_data, axis=0, ignore_index=True)

                final_dataframe['datetime'] = pd.to_datetime(final_dataframe['date'])
                final_dataframe =final_dataframe.sort_values(by='datetime',ascending=True)
                final_dataframe=final_dataframe.set_index('datetime')

                #Add a new column into the dataframe for Ox
                try:
                    final_dataframe['Ox']=final_dataframe['NO2']+final_dataframe['O3']
                except:
                    print("Could not create Ox entry for ", site)

                #Add a new column into the dataframe for Ox
                try:
                    final_dataframe['NOx']=final_dataframe['NO2']+final_dataframe['NO']
                except:
                    print("Could not create NOx entry for ", site)
                # Now save the data frame to a .csv file

                # Now clean the dataframe for missing entries - make this optional!!
                if clean_site_data is True:
                # It might be that not all sites record all pollutants here. In which case I think
                # we just need to cycle through each potential pollutant
                    for entry in ['O3', 'NO2', 'NO', 'PM2.5', 'Ox', 'NOx','temp', 'ws', 'wd']:
                        if entry in final_dataframe.columns.values:
                            #pdb.set_trace()
                            final_dataframe=final_dataframe.dropna(subset=[entry])
                # Now save the dataframe as a .csv file
                if save_to_csv is True:
                    print("Creating .csv file for ", station_name)
                    final_dataframe.to_csv(download_path+"/"+local_authority+"/"+site+'.csv', index = False, header=True)

                # Append entire dataframe to all site catalogue dictionary


                if plot_diurnal_comparison is True:

                    try:

                        textstr = local_authority+', '+station_name+', '+site_type

                        site_data_dict[site] = final_dataframe
                        site_data_dict_name[site] = metadata['AURN_metadata'][metadata['AURN_metadata'].site_id == site]['site_name'].values[0]

                        # Now produce a summary figure of the analysis that includes:
                        # Site name and DEFRA category
                        # Daily profile of NO2 for March and April
                        # Daily profile of Ox for March and April
                        # You can modify the routines below to include more months of course

                        for entry in site_data_dict[site].columns:

                            if entry in ['O3', 'NO2', 'NO', 'PM2.5', 'Ox', 'NOx']:

                                mask_march_tag_20 = (site_data_dict[site].index.month == 3) & (site_data_dict[site].index > '2019-12-30')
                                #mask_march_tag_other = (site_data_dict[site].index.month == 3) & (site_data_dict[site].datetime < '2019-12-30')

                                mask_april_tag_20 = (site_data_dict[site].index.month == 4) & (site_data_dict[site].index > '2019-12-30')
                                #mask_april_tag_other = (site_data_dict[site].index.month == 4) & (site_data_dict[site].datetime < '2019-12-30')

                                mask_march = (site_data_dict[site].index.month == 3)
                                mask_april = (site_data_dict[site].index.month == 4)

                                site_data_dict[site]['March_2020'] = mask_march_tag_20
                                site_data_dict[site]['April_2020'] = mask_april_tag_20

                                f, ax = plt.subplots(2,1,figsize=(15, 10))
                                plt.text(0.02, 0.9, textstr, fontsize=12, transform=plt.gcf().transFigure)
                                sns.boxplot(data=site_data_dict[site].loc[mask_march],x=site_data_dict[site].loc[mask_march].index.hour, y=site_data_dict[site].loc[mask_march][entry],hue='March_2020', ax=ax[0]).set(xlabel='Hour of day',ylabel='Abundance')
                                #ax[0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
                                sns.boxplot(data=site_data_dict[site].loc[mask_april],x=site_data_dict[site].loc[mask_april].index.hour, y=site_data_dict[site].loc[mask_april][entry],hue='April_2020',ax=ax[1]).set(xlabel='Hour of day',ylabel='Abundance')
                                #ax[1].legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
                                plt.savefig(download_path+"/"+local_authority+"/"+local_authority+"-"+station_name+"-"+entry+".png")
                                plt.close('all')
                                #plt.show()

                    except:
                        print("Could not produce figure for ", station_name)
