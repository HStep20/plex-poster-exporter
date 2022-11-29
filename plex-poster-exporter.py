#!/usr/bin/env python3

import os
import sys

# sys
sys.dont_write_bytecode = True
if sys.version_info[0] < 3:
    print("ERROR:", "you must be running python 3.0 or higher.")
    sys.exit()

# click
try:
    import click
except:
    print("ERROR:", "click is not installed.")
    sys.exit()

# plexapi
try:
    import plexapi.utils
    from plexapi.server import PlexServer, CONFIG
    from plexapi.myplex import MyPlexAccount
    from plexapi.exceptions import BadRequest
except:
    print("ERROR:", "plexapi is not installed.")
    sys.exit()

# defaults
NAME = "plex-poster-exporter"
VERSION = 0.2

# plex
class Plex:
    def __init__(
        self,
        token=None,
        base_url=None,
        server=None,
        library=None,
        overwrite=False,
        verbose=False,
    ):

        self.account = None

        self.token = token
        self.base_url = base_url
        self.servers = []
        self.server = PlexServer(baseurl=base_url, token=token)
        self.libraries = []
        self.library = library
        self.overwrite = overwrite
        self.verbose = verbose
        self.downloaded = 0
        self.skipped = 0

        self.getLibrary()

    def getLibrary(self):
        self.libraries = [
            _ for _ in self.server.library.sections() if _.type in {"movie", "show"}
        ]
        if not self.libraries:
            print("ERROR:", "no available libraries.")
            sys.exit()
        if self.library is None or self.library not in [
            _.title for _ in self.libraries
        ]:
            self.library = plexapi.utils.choose(
                "Select Library", self.libraries, "title"
            )
        else:
            self.library = self.server.library.section(self.library)
        if self.verbose:
            print("LIBRARY:", self.library.title)

    def getAll(self):
        return self.library.all()

    def getPath(self, item, season=False):
        if self.library.type == "movie":
            for media in item.media:
                for part in media.parts:
                    return part.file.rsplit("/", 1)[0]
        elif self.library.type == "show":
            for episode in item.episodes():
                for media in episode.media:
                    for part in media.parts:
                        if season:
                            return part.file.rsplit("/", 1)[0]
                        return part.file.rsplit("/", 2)[0]

    def download(self, url=None, filename=None, path=None):
        if not self.overwrite and os.path.isfile(path + "/" + filename):
            if self.verbose:
                print("SKIPPED:", path + "/" + filename)
            self.skipped += 1
        elif plexapi.utils.download(
            self.base_url + url, self.token, filename=filename, savepath=path
        ):
            if self.verbose:
                print("DOWNLOADED:", path + "/" + filename)
            self.downloaded += 1
        else:
            print("DOWNLOAD FAILED:", path + "/" + filename)
            sys.exit()


# main
@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(prog_name=NAME, version=VERSION, message="%(prog)s v%(version)s")
@click.option(
    "--base_url",
    prompt="Base Url",
    help="The Local Network URL for plex.",
    required=True,
)
@click.option("--token", prompt="Plex Token", help="Your Plex Token.", required=True)
@click.option("--server", help="The Plex server name.")
@click.option(
    "--library",
    help="The Plex library name.",
)
@click.option(
    "--assets",
    help="Which assets should be exported?",
    type=click.Choice(["all", "posters", "backgrounds", "banners", "themes"]),
    default="all",
)
@click.option("--overwrite", help="Overwrite existing assets?", is_flag=True)
@click.option("--verbose", help="Show extra information?", is_flag=True)
@click.pass_context
def main(
    ctx,
    base_url: str,
    token: str,
    server: str,
    library: str,
    assets: str,
    overwrite: bool,
    verbose: bool,
):
    overwrite = True
    verbose = True
    plex = Plex(
        token=token,
        base_url=base_url,
        server=server,
        library=library,
        overwrite=overwrite,
        verbose=verbose,
    )

    if verbose:
        print("ASSETS:", assets)
        print("OVERWRITE:", str(overwrite))
        print("\nGetting library items...")

    items = plex.getAll()

    for item in items:
        if verbose:
            print("\nITEM:", item.title)

        path = plex.getPath(item)
        if path is None:
            print("ERROR:", "failed to extract the path.")
            sys.exit()

        if (
            assets in {"all", "posters"}
            and hasattr(item, "thumb")
            and item.thumb != None
        ):
            plex.download(item.thumb, "poster.jpg", path)
        if (
            assets in {"all", "backgrounds"}
            and hasattr(item, "art")
            and item.art != None
        ):
            plex.download(item.art, "background.jpg", path)
        if (
            assets in {"all", "banners"}
            and hasattr(item, "banner")
            and item.banner != None
        ):
            plex.download(item.banner, "banner.jpg", path)
        if (
            assets in {"all", "themes"}
            and hasattr(item, "theme")
            and item.theme != None
        ):
            plex.download(item.theme, "theme.mp3", path)

        if plex.library.type == "show":
            for season in item.seasons():
                path = plex.getPath(season, True)
                if path is None:
                    print("ERROR:", "failed to extract the path.")
                    sys.exit()

                if (
                    assets in ["all", "posters"]
                    and hasattr(season, "thumb")
                    and season.thumb != None
                    and season.title != None
                ):
                    plex.download(
                        season.thumb,
                        (season.title if season.title != "Specials" else "Season 0")
                        + ".jpg",
                        path,
                    )
                    # TODO: Add backgrounds for seasons?
                    # if (assets == 'all' or assets == 'backgrounds') and hasattr(season, 'art') and season.art != None and season.title != None:
                    #     plex.download(season.art, (season.title+'-background' if season.title != 'Specials' else 'season-specials-background')+'.jpg', path)
                    # TODO: Add banners for seasons?
                    # if (assets == 'all' or assets == 'banners') and hasattr(season, 'banner') and season.banner != None and season.title != None:
                    #     plex.download(season.banner, (season.title+'-banner' if season.title != 'Specials' else 'season-specials-banner')+'.jpg', path)

    if verbose:
        print("\nTOTAL SKIPPED:", str(plex.skipped))
        print("TOTAL DOWNLOADED:", str(plex.downloaded))


# run
if __name__ == "__main__":
    main(obj={})
