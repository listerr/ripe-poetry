# ripe-poetry

ripe-poetry is a set of three tools for `poem` objects in the RIPE Database.
A `poem` object is a short poem that a user stores in the database, for example a limerick or a haiku.

| Tool | Purpose |
|------|---------|
| [`ripe-poem`](#ripe-poem) | Write a poem, sign it with GPG, and send it to the RIPE Database by email. |
| [`getpoems.sh`](#getpoemssh) | Download all poems from the RIPE Database into local text files. |
| [`poemstats.py`](#poemstatspy) | Read a file of poems and print tables of counts by year and by author. |

## Requirements

| Tool | Programs that the tool needs |
|------|------------------------------|
| `ripe-poem` | `bash`, `whois`, `awk`, `gpg`, and one mail program: `neomutt`, `sendmail` or `msmtp` |
| `getpoems.sh` | `bash`, `whois`, `curl`, `gzip` and `awk` |
| `poemstats.py` | Python 3.9 or later |

## Install

1. Clone the repository into `~/ripe-poetry`:

   ```
   git clone https://github.com/listerr/ripe-poetry.git ~/ripe-poetry
   ```

2. Go to the directory of the repository:

   ```
   cd ~/ripe-poetry
   ```

3. Make the scripts executable:

   ```
   chmod +x ripe-poem getpoems.sh poemstats.py
   ```

All the commands in this README start in `~/ripe-poetry`.

## ripe-poem

`ripe-poem` creates a `poem` object, signs it with GPG, and sends it to `auto-dbm@ripe.net`.

```
./ripe-poem [-h]
```

The `-h` option shows the usage text.

Each poem has a maintainer and a form.
The maintainer is the `mntner` object that controls changes to your poem.
The form is the poetic form, for example limerick or haiku.
The default maintainer is `LIM-MNT`.
The default form is `FORM-LIMERICK`.

### Set up ripe-poem

On the first run, the script asks you for these values:

- Your RIPE handle, for the `author:` attribute
- The sender email address
- The submission email address (default `auto-dbm@ripe.net`)
- The editor, the `gpg` program and the mail program, with their arguments

To set up `ripe-poem`, do these steps:

1. Run `./ripe-poem`.
2. Type the values.
   The script writes them to `~/.ripe_poem` and sets the file mode to `600`, so that only you can read and write the file.
3. At the prompt `==> Import pgp key? [Y/n]`, press Enter or `y`.
   The script reads the key from the `key-cert` object of the maintainer.
   Then it imports the public key into GPG.
4. Read the output of the import.
   If the `remarks:` lines of the `key-cert` contain a private key, the script also imports the private key.
   Then the script makes a test signature and stops.
5. If you want a different default maintainer or form, edit `MNTNER` and `FORM` in `~/.ripe_poem`.

### Send a poem

Before the editor opens, the script makes sure that the key of the maintainer is in GPG.
If the key is not there, the script imports it.
Then the script makes a test signature.
If the test fails, the script stops with the message `gpg test failed`.

1. Run `./ripe-poem`.
2. Write your poem in the template that opens in the editor.
3. Save the file.
4. Close the editor.
   The script shows the poem and the prompt `[E=Edit, S=Send, A=Abandon]?`.
5. Press one of the letters in the table.

| Letter | Result |
|--------|--------|
| `s` | The script sends the poem. |
| `e` | The editor opens again. This is the default. Any other key also opens the editor. |
| `a` | The script deletes the poem and stops. |

When you press `s`, the script first finds the `poem:` name in the RIPE Database.
If a poem with that name exists, the script compares the `author:` values.
If no author is the same, the script shows a warning with the two authors.
Then it shows the prompt `[E=Edit, S=Send anyway, A=Abandon]?`.
If you send the poem, you change the poem of another author.

The script signs the poem with a GPG clear signature.
With a clear signature, the poem text stays readable, and the signature comes after it.
Then the script sends the poem.
It sends a copy (Cc) to your sender address.

## getpoems.sh

`getpoems.sh` downloads all `poem` objects from the RIPE Database.

```
./getpoems.sh [-o DIR] [-h]
```

| Option | Description |
|--------|-------------|
| `-o DIR` | Write the output files to `DIR`. The default is `~/ripe-poetry/poems`. If the directory does not exist, the script makes it. |
| `-h` | Show the usage text. |

The script does these steps:

1. It downloads `ripe.db.poetic-form.gz` from `ftp.ripe.net` to get the list of poetic forms.
2. It sends one inverse `whois` query to `whois.ripe.net` for each form.
   An inverse query finds all objects that have a given value in one attribute.
   Here, the attribute is `form:`.
3. It writes one file for each form.
4. It writes one merged file that has the date of the run in its name.

The table shows the output files in the default output directory.

| Output file | Content |
|-------------|---------|
| `poems/poems-<FORM>.txt` | The poems of one form, for example `poems-FORM-HAIKU.txt` |
| `poems/ripe.db.poem.<YYYYMMDD>` | All poems from all forms |

## poemstats.py

`poemstats.py` reads a text file that contains `poem` objects.
You can use the merged file from `getpoems.sh` as the input file.

```
./poemstats.py years   FILE [--start YEAR] [--end YEAR] [--authors-max N] [--totals]
./poemstats.py authors FILE [--top N] [--include-no-author | --exclude-no-author] [--totals]
```

### years

The `years` option prints one row for each year, with the number of poems and the number of authors.
It uses the `created:` attribute to find the year.
Years without poems show a count of 0.

| Option | Description |
|--------|-------------|
| `--start YEAR` | First year to show. The default is the first year in the data. |
| `--end YEAR` | Last year to show. The default is the last year in the data. |
| `--authors-max N` | Add a column with the N authors that have the most poems in each year. If the year has more authors, the column ends with `+<count> more`. |
| `--totals` | Add a row with the totals. |

### authors

The `authors` option prints the number of poems for each author, with the largest count first.

| Option | Description |
|--------|-------------|
| `--top N` | Show only the first N authors. |
| `--include-no-author` | Count poems without an author as `(no author)`. |
| `--exclude-no-author` | Do not count poems without an author. This is the default. |
| `--totals` | Add a row with the number of authors and the number of poems. |

### Examples

```
./poemstats.py years poems/ripe.db.poem.20261030 --totals
./poemstats.py years poems/ripe.db.poem.20261030 --start 2003 --end 2026 --authors-max 3
./poemstats.py authors poems/ripe.db.poem.20261030 --top 10 --totals
```
