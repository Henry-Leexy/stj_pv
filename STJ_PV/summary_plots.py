#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Make a summarising plot of a jet finding expedition."""
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

plt.style.use('fivethirtyeight')
plt.rc('savefig', edgecolor='#ffffff', facecolor='#ffffff')
plt.rc('axes', facecolor='#ffffff', edgecolor='#ffffff')
plt.rc('figure', facecolor='#ffffff', edgecolor='#ffffff')

__author__ = 'Michael Kelleher'


def main(run_name=None, props=None):
    """Load jet run output, make a plot or two."""
    plt.rc('font', family='sans-serif', size=9)
    if props is None:
        props = {'pv': 2.0,
                 'fit': 6,
                 'y0': 10.0,
                 'yN': 65.0,
                 'zonal_reduce': 'mean',
                 'date_s': '1979-01-01',
                 'date_e': '2018-12-31'}

    if run_name is None:
        props['data'] = 'ERAI_MONTHLY_THETA_STJPV'

    elif run_name == 'sample':
        props = {'pv': 2.0,
                 'fit': 6,
                 'y0': 10.0,
                 'yN': 65.0,
                 'zonal_reduce': 'mean',
                 'date_s': '2016-01-01',
                 'date_e': '2016-01-03'}
        props['data'] = 'NCEP_NCAR_DAILY_STJPV'

    elif 'MERRA2' in run_name:
        props['data'] = run_name
        props['date_s'] = '1980-01-01'
        props['date_e'] = '2018-12-31'

    else:
        props['data'] = run_name

    in_file = ('{data}_pv{pv:.1f}_fit{fit}_y0{y0:03.1f}_yN{yN:.1f}_'
               'z{zonal_reduce}_{date_s}_{date_e}'.format(**props))

    data = xr.open_dataset('./jet_out/{}.nc'.format(in_file))
    print(f'DATA COMMIT: {data.attrs["commit-id"]}')
    month_mean = data.groupby('time.month').mean()
    month_std = data.groupby('time.month').std()

    fig_width = 17.4 / 2.54
    figh_height = fig_width * 0.6
    fig = plt.figure(figsize=(fig_width, figh_height))
    axes = [plt.subplot2grid((2, 2), (0, 0)), plt.subplot2grid((2, 2), (0, 1)),
            plt.subplot2grid((2, 2), (1, 0), colspan=2)]
    cline_w = 3.0
    color_nh = '#1E5AAF'
    color_sh = '#B711A3'

    for hidx, hem in enumerate(['sh', 'nh']):
        sct = axes[hidx].scatter(data['lat_{}'.format(hem)],
                                 data['theta_{}'.format(hem)],
                                 s=0.3 * data['intens_{}'.format(hem)]**2,
                                 c=data['intens_{}'.format(hem)],
                                 marker='.', cmap='inferno',
                                 vmin=0., vmax=45., alpha=0.3)

        # Hexbins? Maybe...
        # sct = axes[hidx].hexbin(data[f'lat_{hem}'].values,
        #                         data[f'theta_{hem}'].values,
        #                         gridsize=20, cmap='Blues', mincnt=1,
        #                         edgecolors='k', linewidths=0.1)

        axes[hidx].set_ylabel('Theta Position [K]')
        if hem == 'nh':
            cax = fig.add_axes([0.49, 0.51, 0.02, 0.4])
            cbar = plt.colorbar(sct, cax=cax, orientation='vertical')
            cbar.set_label('Jet intensity [m/s]')
            cax.yaxis.set_label_position('left')
            axes[hidx].tick_params(left=False, labelleft=False, labeltop=False,
                                   right=True, labelright=True)
            axes[hidx].ticklabel_format(axis='y', style='plain')
            axes[hidx].yaxis.set_label_position('right')

        axes[hidx].set_xlabel('Latitude Position [deg]')
        axes[hidx].set_title(HEM_INFO[hem]['label'])
        axes[hidx].set_ylim([320, 375])
        # axes[hidx].set_ylim([330, 385])
        axes[hidx].set_xlim(HEM_INFO[hem]['lat_r'])

    ln_nh = axes[2].plot(month_mean.month, month_mean['lat_nh'].values,
                         'o-', color=color_nh, lw=cline_w,
                         ms=cline_w * 1.5, label='NH', zorder=5)

    axes[2].fill_between(month_mean.month,
                         month_mean['lat_nh'] + month_std['lat_nh'],
                         month_mean['lat_nh'] - month_std['lat_nh'],
                         color=color_nh, alpha=0.4, zorder=4)
    axes[2].fill_between(month_mean.month,
                         month_mean['lat_nh'] + 2 * month_std['lat_nh'],
                         month_mean['lat_nh'] - 2 * month_std['lat_nh'],
                         color=color_nh, alpha=0.1, zorder=3)

    axes[2].set_ylim(HEM_INFO['nh']['lat_r'])
    axes[2].set_ylabel('Jet Latitude')
    # axes[2].set_yticklabels(axes[2].get_yticks(),

    axis_sh = axes[2].twinx()

    ln_sh = axis_sh.plot(month_mean.month, month_mean['lat_sh'], 'o-',
                         lw=cline_w, label='SH', color=color_sh)

    axis_sh.fill_between(month_mean.month,
                         month_mean['lat_sh'] + month_std['lat_sh'],
                         month_mean['lat_sh'] - month_std['lat_sh'],
                         color=color_sh, alpha=0.4)

    axis_sh.fill_between(month_mean.month,
                         month_mean['lat_sh'] + 2 * month_std['lat_sh'],
                         month_mean['lat_sh'] - 2 * month_std['lat_sh'],
                         color=color_sh, alpha=0.1)
    axis_sh.set_ylim(HEM_INFO['sh']['lat_r'])

    axis_sh.tick_params(left=False, labelleft=False, labeltop=False,
                        right=False, labelright=False)
    axis_sh.set_xticks(np.arange(1, 13))
    axis_sh.set_xticklabels(['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                             'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'])

    lns = ln_nh + ln_sh
    labs = [l.get_label() for l in lns]
    axes[2].legend(lns, labs, loc=0, frameon=False)
    axes[2].set_axisbelow(True)
    axes[2].grid(b=True, zorder=-1)
    axes[2].xaxis.grid(b=False)
    axis_sh.grid(b=False)
    axis_sh.invert_yaxis()

    fig.subplots_adjust(left=0.08, bottom=0.05, right=0.92, top=0.94,
                        wspace=0.23, hspace=0.28)
    out_file = in_file.replace('.', 'p')
    plt.savefig('{}.{}'.format(out_file, EXTN))
    pair_grid(data, out_file)
    summary_table(data, out_file)


def pair_grid(data, out_file):
    """Make PairGrid plot for each hemisphere."""
    dframe = data.to_dataframe()
    dframe = dframe.dropna()
    nh_vars = ['{}_nh'.format(var) for var in ['theta', 'lat', 'intens']]
    sh_vars = ['{}_sh'.format(var) for var in ['theta', 'lat', 'intens']]
    df_nh = dframe[nh_vars]
    df_sh = dframe[sh_vars]

    for hem, dfi in [('nh', df_nh), ('sh', df_sh)]:
        dfi = dfi.rename(index=str,
                         columns={'lat_{}'.format(hem): 'Latitude [deg]',
                                  'theta_{}'.format(hem): 'Theta [K]',
                                  'intens_{}'.format(hem): 'Intensity [m/s]'})
        dfi['season'] = SEAS[pd.DatetimeIndex(dfi.index).month].astype(str)
        grd = sns.PairGrid(dfi, diag_sharey=False, hue='season',
                           palette=HEM_INFO[hem]['pal'])
        grd.fig.set_size_inches(17.4 / 2.54, 17.4 / 2.54)
        grd.map_lower(plt.scatter, marker='o', alpha=0.8, s=6.0)
        grd.map_diag(sns.kdeplot, lw=2)
        plt.suptitle('{} Properties'.format(HEM_INFO[hem]["label"]))
        grd.fig.subplots_adjust(top=0.92)
        grd.add_legend(frameon=False)

        # Because we've separated by hue, have to do KDE plots separately
        for i, j in zip(*np.triu_indices_from(grd.axes, 1)):
            sns.kdeplot(dfi[grd.x_vars[j]], dfi[grd.y_vars[i]],
                        shade=True, cmap='Reds', legend=False,
                        shade_lowest=False, ax=grd.axes[i, j])
        plt.savefig('plt_grid_{}_{}.{}'.format(hem, out_file, EXTN))
        plt.clf()
        plt.close()


def summary_table(data_in, out_file):
    """Compute monthly, seasonal, and annual mean for NH and SH."""
    data_seasonal = data_in.groupby('time.season').mean()
    data_monthly = data_in.groupby('time.month').mean()

    # Set output precision
    pd.set_option('display.float_format', lambda x: '%.1f' % x)
    var_order = ['lat_sh', 'lat_nh', 'intens_sh',
                 'intens_nh', 'theta_sh', 'theta_nh']
    annual = pd.DataFrame({'Annual': data_in.to_dataframe().mean()}).T
    seasonal = data_seasonal.to_dataframe()
    annual = annual.append(seasonal)[var_order]
    with open('seasonal_stats_{}.tex'.format(out_file), 'w') as fout:
        fout.write(annual.to_latex())

    with open('monthly_stats_{}.tex'.format(out_file), 'w') as fout:
        fout.write(data_monthly.to_dataframe().to_latex())

    with open('annual_stats_{}.tex'.format(out_file), 'w') as fout:
        fout.write(annual.T.to_latex())


# Color map for seasons
EXTN = 'pdf'

COLS = {'summer': sns.xkcd_rgb['red'],
        'winter': sns.xkcd_rgb['denim blue'],
        'spring': sns.xkcd_rgb['medium green'],
        'autumn': sns.xkcd_rgb['pumpkin orange']}

HEM_INFO = {'nh': {'label': 'Northern Hemisphere', 'lat_r': (19, 51),
                   'pal': [COLS['winter'], COLS['spring'],
                           COLS['summer'], COLS['autumn']]},
            'sh': {'label': 'Southern Hemisphere', 'lat_r': (-51, -19),
                   'pal': [COLS['summer'], COLS['autumn'],
                           COLS['winter'], COLS['spring']]}}

SEAS = np.array([None, 'DJF', 'DJF', 'MAM', 'MAM', 'MAM', 'JJA',
                 'JJA', 'JJA', 'SON', 'SON', 'SON', 'DJF'])

if __name__ == '__main__':
    DATASETS = ['ERAI_MONTHLY_THETA_STJPV', 'ERAI_DAILY_THETA_STJPV',
                'MERRA2_MONTHLY_STJPV', 'MERRA2_DAILY_STJPV',
                'JRA55_MONTHLY_STJPV', 'JRA55_DAILY_STJPV',
                'CFSR_DAILY_THETA_STJPV', 'CFSR_MONTHLY_THETA_STJPV']

    for RNAME in DATASETS:
        main(run_name=RNAME)
