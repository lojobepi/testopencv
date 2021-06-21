# %%
import pandas as pd
from datetime import datetime


# %%
df = pd.DataFrame(columns=['DateTime', 'Plate', 'Direction', 'Source'])

df.head()
# %%
df = df.append({'DateTime':datetime.now(), 'Plate':'ABF7059', 'Direction':'ENTERING', 'Source':'camera'}, ignore_index=True)
df.head()
# %%
df.to_excel('data.xlsx')
# %%
rdf = pd.read_excel('residents.xlsx')
rdf.head()
# %%
r = rdf[rdf.Plate == 'ABF705']
print(len(r))

# %%


today = str.replace(f'{datetime.now()}',':', '_')
print(today)

# %%
import os
import glob
all_files = glob.glob(os.path.join('Car/*.mp4'))

for filename in all_files:
    print(filename)
    #print(os.path.basename(filename))

# %%