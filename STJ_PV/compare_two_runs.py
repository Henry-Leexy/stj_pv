# -*- coding: utf-8 -*-
"""Script to compare two or more runs of STJ Find."""
import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import numpy as np
import seaborn as sns

SEASONS = np.array([None, 'DJF', 'DJF', 'MAM', 'MAM', 'MAM',
                    'JJA', 'JJA', 'JJA', 'SON', 'SON', 'SON', 'DJF'])

HEMS = {'nh': 'Northern Hemisphere', 'sh': 'Southern Hemisphere'}

class FileDiag(object):
    """
    Contains information about an STJ metric output file in a DataFrame.
    """
    def __init__(self, info):
        self.name = info['label']
        self.d_s = xr.open_dataset(info['file'])
        self.dframe = None
        self.vars = None

        var, self.start_t, self.end_t = self.make_dframe()
        self.metric = var

    def make_dframe(self):
        """Creates dataframe from input netCDF / xarray."""
        hems = ['nh', 'sh']
        self.dframe = self.d_s.to_dataframe()

        self.vars = set([var.split('_')[0] for var in self.dframe])
        dframes = [[pd.DataFrame({var: self.dframe['{}_{}'.format(var, hem)], 'hem': hem})
                    for hem in hems] for var in self.vars]
        dframes_tmp = [frame[0].append(frame[1]) for frame in dframes]
        metric = pd.DataFrame()
        for frame in dframes_tmp:
            metric = metric.append(frame)

        metric['season'] = SEASONS[metric.index.month].astype(str)
        metric['kind'] = self.name

        return metric, self.dframe.index[0], self.dframe.index[-1]

    def append(self, other):
        """Append the DataFrame attribute (self.lats) to another FileDiag's DataFrame."""
        assert isinstance(other, FileDiag)
        return self.metric.append(other.metric)

    def __sub__(self, other):
        hems = ['nh', 'sh']

        df1 = self.metric
        df2 = other.metric

        # Get a set of all variables common to both datasets
        var_names = self.vars.intersection(other.vars)

        # Initialise a list of differences of the variables between datasets
        diff = []
        for var in var_names:
            # Separate hemispheres for `var` one list for self, one for other
            inside = [df1[df1.hem == hem][var] for hem in hems]
            outside = [df2[df2.hem == hem][var] for hem in hems]
            # For each hemisphere, make the difference of self - other a DataFrame
            diff_c = [pd.DataFrame({var: inside[idx] - outside[idx], 'hem': hems[idx]})
                      for idx in range(len(hems))]

            # Combine the two hemispheres into one DF
            diff.append(diff_c[0].append(diff_c[1]))

        diff_out = pd.DataFrame()
        for frame in diff:
            diff_out = diff_out.append(frame)

        diff_out['season'] = SEASONS[diff_out.index.month].astype(str)
        return diff_out


def main():
    """Selects two files to compare, loads and plots them."""
    file_info = {
        'NCEP-PV': {'file': './NCEP_NCAR_MONTHLY_STJPV_pv2.0_fit12_y010.0.nc',
                    'label': 'NCEP PV'},
        'NCEP-Umax': {'file': './NCEP_NCAR_MONTHLY_HR_STJUMax_pres25000.0_y010.0.nc',
                      'label': 'NCEP U-max'},
        'ERAI-Theta': {'file': './ERAI_MONTHLY_THETA_STJPV_pv2.0_fit8_y010.0.nc',
                       'label': 'ERAI Theta'},
        'ERAI-Pres': {'file': './ERAI_PRES_STJPV_pv2.0_fit10_y010.0.nc',
                      'label': 'ERAI PV'},
        'ERAI-KP': {'file': './ERAI_PRES_KangPolvani_1979-01-01_2016-01-01.nc',
                    'label': 'ERAI K-P'}
    }

    fig_width = 110 / 25.4
    in_names = ['NCEP-PV', 'NCEP-Umax']
    fds = [FileDiag(file_info[in_name]) for in_name in in_names]

    assert fds[0].start_t == fds[1].start_t, 'Start dates are different'
    assert fds[0].end_t == fds[1].end_t, 'End dates are different'

    data = fds[0].append(fds[1])
    diff = fds[0] - fds[1]

    # Make violin plot grouped by hemisphere, then season
    fig, axes = plt.subplots(2, 1, figsize=(fig_width, fig_width * 2))
    sns.violinplot(x='season', y='lat', hue='kind', data=data[data.hem == 'nh'],
                   split=True, inner='quart', ax=axes[0], cut=0)
    sns.violinplot(x='season', y='lat', hue='kind', data=data[data.hem == 'sh'],
                   split=True, inner='quart', ax=axes[1], cut=0)
    fig.legend()
    for axis in axes:
        axis.legend_.remove()

    plt.savefig('plt_dist.png')
    plt.close()


    # Make timeseries plot for each hemisphere, and difference in each
    fig, axes = plt.subplots(2, 2, figsize=(15, 5))
    for idx, dfh in enumerate(data.groupby('hem')):
        hem = dfh[0]
        axes[idx, 1].plot(diff.lat[diff.hem == hem])

        for kind, dfk in dfh[1].groupby('kind'):
            axes[idx, 0].plot(dfk.lat, label=kind)
        axes[idx, 0].set_title(HEMS[hem])
        axes[idx, 1].set_title('{} Difference'.format(HEMS[hem]))
        axes[idx, 0].grid(b=True, ls='--')
        axes[idx, 1].grid(b=True, ls='--')

    axes[0, 0].legend()
    plt.tight_layout()
    plt.savefig('plt_diff_timeseries.png')

    # Make a bar chart of mean difference
    sns.factorplot(x='season', y='lat', col='hem', data=diff, kind='bar')
    plt.tight_layout()
    plt.savefig('plt_diff_bar.png')


if __name__ == "__main__":
    main()
