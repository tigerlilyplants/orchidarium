# Orchidarium

![GitHub Release](https://img.shields.io/github/v/release/tigerlilyobservatory/orchidarium)

<p align="left" width="100%">
  <img width="20%" src="./img/orchid.png" alt="orchid">
</p>

A collection of scripts and configuration files for collecting and publishing metrics from USB sensors in an orchid terrarium.

Current supported sensors by this Python package include a

- [Humidity and Temperature sensor](https://www.amazon.com/dp/B08BYLZ3ML?ref=ppx_yo2ov_dt_b_fed_asin_title): a waterproof temperature and humidity sensor.
- [Soil metrics](https://www.amazon.com/dp/B0FJFK9PPT?ref=ppx_yo2ov_dt_b_fed_asin_title): a sensor for collecting soil analytics.

## Build

<p align="left" width="100%">
  <img width="75%" src="img/40DB1760-932C-47B8-96B4-398F92D82769_1_105_c.jpeg" alt="build">
</p>

I've sourced a lot of components from various sites for this build.

- Here's a [public Amazon list](https://www.amazon.com/hz/wishlist/ls/1ARZ5WK7A2QLO?ref_=wl_share) with most of the hardware I used to get this orchidarium off the ground.
- I sourced the large cork bark log [from a seller on Etsy](https://www.etsy.com/listing/1855324948/oversize-cork-rounds-cut-to-length?ref=yr_purchases) who specializes in terrariums.
- Many of the orchids that have been mounted in the terrarium are from ecuagenera, as well as a number of other retail sellers and auctions. Begonias and other terrestrial plants have been sourced from various sellers on Etsy, including [Botanicaz](https://www.etsy.com/shop/Botanicaz?ref=yr_purchases) and [FloraEpiphytica](https://www.etsy.com/shop/FloraEpiphytica?ref=yr_purchases).

This is the second terrarium I've built, following the first (pictured below).

<p align="left" width="100%">
  <img width="75%" src="./img/D9408F09-C330-4E73-A14A-539844C02985_1_105_c.jpeg" alt="first terrarium I built">
</p>

## How it works by example

See the below screenshots from the Grafana dashboard.

## Local development

### Setup

1. Copy the [`udev.rules`](./rules/.rules) to `/etc/udev/rules.d/orchidarium.rules`. You'll notice I've matched the IDs of the USB devices purchased at the links above to the IDs found via [`lsusb -v`](./refs/lsusb.out).
2. Plug in USB devices or run `sudo udevadm control --reload-rules` to reload rules.
3. Source [`./scripts/.env.sh`](./scripts/.env.sh) to get started with environment variables populated from a Linux pass store.
4. The [`compose.yaml`](./compose.yaml) contains the configuration required to get this project started.

   ```text
   docker compose up -d --build
   ```
