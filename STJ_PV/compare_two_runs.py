# -*- coding: utf-8 -*-
"""Script to compare two or more runs of STJ Find."""
import os
import yaml
import pandas as pd
from pandas.plotting import register_matplotlib_converters
import matplotlib.pyplot as plt
import xarray as xr
import numpy as np
import seaborn as sns

register_matplotlib_converters()
SEASONS = np.array([None, 'DJF', 'DJF', 'MAM', 'MAM', 'MAM',
                    'JJA', 'JJA', 'JJA', 'SON', 'SON', 'SON', 'DJF'])

HEMS = {'nh': 'Northern Hemisphere', 'sh': 'Southern Hemisphere'}


class FileDiag(object):
    """
    Contains information about an STJ metric output file in a DataFrame.
    """

    def __init__(self, info, opts_hem=None, file_path=None):
        self.name = info['label']
        if file_path is None:
            # If the file path is not provided, the input path in `info` is the abs path
            file_path = ''
        self.d_s = xr.open_dataset(os.path.join(file_path, info['file']))
        if 'level' in self.d_s:
            self.d_s = self.d_s.drop('level')

        self.dframe = None
        self.vars = None
        self.opt_hems = opts_hem

        var, self.start_t, self.end_t = self.make_dframe()
        self.metric = var

    def make_dframe(self):
        """Creates dataframe from input netCDF / xarray."""
        if self.opt_hems is None:
            hems = ['nh', 'sh']
        else:
            # in case you want to use equator or only one hemi
            hems = self.opt_hems

        self.dframe = self.d_s.to_dataframe()

        self.vars = set([var.split('_')[0] for var in self.dframe])
        if 'time' in self.vars:
            self.vars.remove('time')
        dframes = [
            [
                pd.DataFrame({var: self.dframe['{}_{}'.format(var, hem)], 'hem': hem})
                for var in self.vars
            ]
            for hem in hems
        ]
        dframes_tmp = []
        for frames in dframes:
            metric_hem = None
            for frame in frames:
                # Add a time column so that the merge works
                # Bit of a hack, because we only use up to daily data, we can drop
                # hours, so in case that's different between datasets, they compare fine
                # using the .normalize() function of a Pandas DatetimeIndex

                # This will need to be revisited probably when using CMIP data with
                # non-real world calendars. But that's a problem for a different day :-)
                _times = pd.DatetimeIndex(frame.index)
                frame['time'] = _times.normalize()

                if metric_hem is None:
                    metric_hem = frame
                else:
                    # to avoid the following error:
                    # *** ValueError: 'time' is both an index level and a
                    # column label, which is ambiguous.
                    metric_hem.index.name = None
                    frame.index.name = None
                    metric_hem = metric_hem.merge(frame)

            dframes_tmp.append(metric_hem)

        metric = dframes_tmp[0].append(dframes_tmp[1])

        if len(hems) == 3:  # If eq is also wanted
            metric = metric.append(dframes_tmp[2])
        # metric['time'] = metric.index
        metric['season'] = SEASONS[pd.DatetimeIndex(metric.time).month].astype(str)
        metric['kind'] = self.name

        # Make all times have Hour == 0
        times = pd.DatetimeIndex(metric['time'])
        if all(times.hour == times[0].hour):
            times -= pd.Timedelta(hours=times[0].hour)

        metric = metric.set_index(times)
        return metric, metric.index[0], metric.index[-1]

    def append_metric(self, other):
        """Append the DataFrame attribute (self.lats) to another FileDiag's DataFrame."""
        assert isinstance(other, FileDiag)
        return self.metric.append(other.metric, sort=False)

    def time_subset(self, other):
        """Make two fds objects have matching times."""
        if self.metric.shape[0] > other.metric.shape[0]:
            # self is bigger
            fds0 = self.metric.loc[sorted(other.metric.time[other.metric.hem == 'nh'])]
            self.metric = fds0
            self.start_t = self.metric.index[0]
            self.end_t = self.metric.index[-1]
        elif self.metric.shape[0] < other.metric.shape[0]:
            # other is bigger
            fds1 = other.metric.loc[sorted(self.metric.time[self.metric.hem == 'nh'])]
            other.metric = fds1
            other.start_t = other.metric.index[0]
            other.end_t = other.metric.index[-1]

        else:
            # Temp single hemisphere to check time resolutions
            o_hem = other.metric[other.metric.hem == 'nh']
            s_hem = self.metric[self.metric.hem == 'nh']
            s_tres = (s_hem.time[-1] - s_hem.time[0]) / s_hem.shape[0]
            o_tres = (o_hem.time[-1] - o_hem.time[0]) / o_hem.shape[0]

            if abs(o_hem.time[0] - s_hem.time[0]) < max(o_tres, s_tres):
                # Difference in start times is smaller than time resolution
                # so treat both times as the same
                self.metric = self.metric.set_index(other.metric.index)
                self.metric['time'] = self.metric.index
            else:
                raise ValueError('Times do not match, cannot compare')

    def __sub__(self, other):
        hems = ['nh', 'sh']

        df1 = self.metric
        df2 = other.metric
        assert (df1.time - df2.time).sum() == pd.Timedelta(0), 'Not all times match'

        # Get a set of all variables common to both datasets
        var_names = self.vars.intersection(other.vars)

        # Initialise a list of differences of the variables between datasets
        diff = []
        for var in var_names:
            # Separate hemispheres for `var` one list for self, one for other
            inside = [df1[df1.hem == hem][var] for hem in hems]
            outside = [df2[df2.hem == hem][var] for hem in hems]

            # For each hemisphere, make the difference of self - other a DataFrame
            diff_c = [
                pd.DataFrame(
                    {
                        var: inside[idx] - outside[idx],
                        'hem': hems[idx],
                        'time': df1[df1.hem == hems[idx]].time,
                    }
                )
                for idx in range(len(hems))
            ]

            # Combine the two hemispheres into one DF
            diff.append(diff_c[0].append(diff_c[1]))

            diff_out = None
            for frame in diff:
                if diff_out is None:
                    diff_out = frame
                else:
                    diff_out.index.name = None
                    frame.index.name = None
                    diff_out = diff_out.merge(frame)
        diff_out['season'] = SEASONS[pd.DatetimeIndex(diff_out.time).month].astype(str)
        return diff_out


def main():
    """Selects two files to compare, loads and plots them."""
    with open("runinfo.yml") as cfgin:
        file_info = yaml.safe_load(cfgin.read())

    nc_dir = './jet_out'
    # nc_dir = '/home/pm366/Documents/Data/'
    if not os.path.exists(nc_dir):
        nc_dir = '.'

    fig_mult = 1.0
    plt.rc('font', size=9 * fig_mult)
    extn = 'pdf'
    sns.set_style('whitegrid')
    fig_width = (8.4 / 2.54) * fig_mult
    fig_height = fig_width * 1.3

    in_names = ['ERAI-Monthly', 'ERAI-DavisBirner']
    # Make a list with just the labels (since this is what the dataframe will have in it
    labels = [file_info[in_name]['label'] for in_name in in_names]
    # Define a colour for each kind
    colors = ['C1', 'C0']
    # And make a dict to map label -> colour
    color_map = dict(zip(labels, colors))

    fds = [FileDiag(file_info[in_name], file_path=nc_dir) for in_name in in_names]

    data = fds[0].append_metric(fds[1])

    # Make violin plot grouped by hemisphere, then season
    # NOTE: I've changed the seaborn.violinplot code to make the quartile lines
    # solid rather than dashed, may want to come back to this and figure out a way
    # to implement it in a nice (non-hacked!) way for others and PR it to seaborn
    fig, axes = plt.subplots(2, 1, figsize=(fig_width, fig_height), sharex=True)
    sns.violinplot(
        x='season',
        y='lat',
        hue='kind',
        data=data[data.hem == 'nh'],
        split=True,
        inner='quart',
        ax=axes[0],
        cut=0,
        linewidth=1.0 * fig_mult,
        dashpattern='-',
        palette=colors,
    )
    axes[0].set_yticks(np.arange(30, 60, 10))

    sns.violinplot(
        x='season',
        y='lat',
        hue='kind',
        data=data[data.hem == 'sh'],
        split=True,
        inner='quart',
        ax=axes[1],
        cut=0,
        linewidth=1.0 * fig_mult,
        dashpattern='-',
        palette=colors,
    )
    axes[1].set_yticks(np.arange(-50, -20, 10))
    for axis in axes:
        axis.set_xlabel('')
        axis.set_ylabel('Latitude [deg]')
    fig.subplots_adjust(left=0.13, bottom=0.05, right=0.98, top=0.98, hspace=0.0)

    for axis in axes:
        axis.legend_.remove()
        axis.tick_params(axis='y', rotation=90)
        axis.grid(b=True, ls='--', zorder=-1)
    axes[1].legend(bbox_to_anchor=(0.5, 0.05), loc='lower center', borderaxespad=0.0)
    # fig.suptitle('Seasonal jet latitude distributions')

    plt.savefig('plt_dist_{}-{}.{ext}'.format(ext=extn, *in_names))
    plt.close()

    if fds[0].start_t != fds[1].start_t or fds[0].end_t != fds[1].end_t:
        fds[0].time_subset(fds[1])

    diff = fds[0] - fds[1]

    # Make timeseries plot for each hemisphere, and difference in each
    # fig, axes = plt.subplots(2, 2, figsize=(15, 5))
    _width = 174
    fig_width = _width * fig_mult
    figsize = (fig_width / 25.4, (fig_width * (9 / 16) / 25.4))

    fig_ts, axes_ts = plt.subplots(2, 1, figsize=figsize)
    fig_diff, axes_diff = plt.subplots(2, 1, figsize=figsize)

    for idx, dfh in enumerate(data.groupby('hem')):
        hem = dfh[0]
        axes_diff[idx].plot(diff.time[diff.hem == hem], diff.lat[diff.hem == hem])

        for kind, dfk in dfh[1].groupby('kind'):
            axes_ts[idx].plot(dfk.lat, label=kind, color=color_map[kind])
            print(f"{kind:20s} {hem} mean: {dfk.lat.mean():.1f} std: {dfk.lat.std():.1f}")

        axes_ts[idx].set_title(HEMS[hem])
        if hem == 'nh':
            axes_ts[idx].set_ylim([20, 50])
        else:
            axes_ts[idx].set_ylim([-50, -20])
        # axes_diff[idx].set_ylim([-20, 20])
        axes_diff[idx].set_title('{} Difference'.format(HEMS[hem]))
        axes_ts[idx].grid(b=True, ls='--')
        axes_diff[idx].grid(b=True, ls='--')

    axes_ts[0].legend()

    fig_ts.tight_layout()
    fig_diff.tight_layout()

    fig_ts.savefig('plt_timeseries_{}-{}.{ext}'.format(ext=extn, *in_names))
    fig_diff.savefig('plt_timeseries_diff_{}-{}.{ext}'.format(ext=extn, *in_names))

    # Make a bar chart of mean difference
    sns.catplot(x='season', y='lat', col='hem', data=diff, kind='bar')
    plt.tight_layout()
    plt.savefig('plt_diff_bar_{}-{}.{ext}'.format(ext=extn, *in_names))


if __name__ == "__main__":
    main()
