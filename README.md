# beets-listenbrainz
A plugin for [beets](https://github.com/beetbox/beets) to interface with ListenBrainz.

## Installation

Install the plugin using `pip`:

```shell
pip install git+https://github.com/arsaboo/beets-listenbrainz.git
```

Then, [configure](#configuration) the plugin in your
[`config.yaml`](https://beets.readthedocs.io/en/latest/plugins/index.html) file.

## Configuration

Add `listenbrainz` to your list of enabled plugins.

```yaml
plugins: listenbrainz
```

Next, you can configure ListenBrainz like following (see instructions to obtain ListenBrainz token [here](https://listenbrainz.readthedocs.io/en/latest/users/api/index.html#get-the-user-token)).

```yaml
listenbrainz:
    token: listenbrainz_token
    username: listenbrainz_user
```