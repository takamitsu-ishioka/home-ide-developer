# home-ide-developer

🇺🇸 English | [🇯🇵 日本語](README.ja.md)

> **Your home directory is an IDE.**

This is not a collection of configuration files.

At least, that is not what its author intends it to be.

`~/.bashrc`, `~/bin`, Git, Python, Claude Code, WSL, and a small army of shell scripts.

Things normally dismissed as the *surroundings* of a development environment are assembled here with a different ambition:

**to turn the home directory itself into the development environment.**

The name is **home-ide-developer**.

You do not install the IDE.

**You turn the place where you live into one.**

---

## Why does this exist?

Long ago, people working with UNIX noticed something peculiar.

UNIX did not really have a giant thing called a "development environment."

There was an editor.
There was a shell.
There was a compiler.
There was `grep`.
There was `sed`.
There was `awk`.
There was Git.

And they could all be connected.

```text
small tool
    |
    +-- small tool
    |       |
    |       +-- small tool
    |               |
    +---------------+
            |
           work
```

In other words:

> **UNIX itself was the IDE.**

So what should an IDE look like in 2026, in the age of generative AI?

Perhaps the answer has not changed very much.

---

## AI is not "a feature inside the IDE"

This repository does not treat AI as something special.

AI can write code.
It can investigate.
It can design.
It can test.
It can write documentation.

But none of that automatically becomes an asset.

If every time you use AI you have to explain:

> "Read this file, do this, then do that, then take the result and..."

you are not very far removed from a human clicking through the same GUI every time.

So we reverse the idea.

**Let AI manufacture parts.**

When an operation works well once, turn it into a bash or Python command.

```bash
$ something-useful input output
```

Next time, both humans and AI can simply use it.

Reasoning fluctuates.

**Commands don't.**

The smarter AI becomes, the more valuable it becomes to build systems in which AI does **not** have to think about the same thing twice.

---

## `~/bin` is a second brain

Suppose you encounter an annoying task.

The first time, you do it manually.

The second time, you do it manually again and feel mildly ashamed.

The third time you are about to do it manually—

**write a script.**

For example:

```bash
$ foo-fetch ...
$ foo-convert ...
$ foo-compare ...
```

Now today's you no longer needs to think about what yesterday's you already figured out.

This is more than "automation."

It is **the compilation of thought**.

Human judgment is transformed into something executable and reproducible.

Then the result goes into `~/bin`.

As this environment is used, the home directory gradually becomes a little smarter than its owner.

Even if the owner forgets, `~/bin` remembers.

Probably.

---

## This repository does not hate GUIs

GUIs are wonderful.

If you want to look at photographs, use a GUI.
If you want to explore a map, use a GUI.
If you want to draw, use a GUI.

The problem begins when you need to:

> **repeat exactly the same operation again and again.**

If a human repeatedly has to:

1. open an application,
2. choose a menu,
3. select a file,
4. configure some options,
5. press a button,

then perhaps the operation is simply **a command that has not been born yet**.

In this repository, useful operations discovered through GUIs are turned into CLI operations whenever practical.

GUIs are good at exploration.

CLIs are good at reproduction.

**Let humans and AI explore. Let programs reproduce.**

---

## Bugs grow on boundaries

If the philosophy of this repository had to be reduced to a single sentence, it might be this:

> **Bugs grow on boundaries.**
> — Kisaburo Yamada

Windows to WSL.
GUI to CLI.
JSON to objects.
Humans to AI.
AI to scripts.
One department to another.

At every boundary, something gets translated.

And when something gets translated:

* meanings shift,
* information disappears,
* implicit assumptions multiply,
* and someone eventually says, "Well, it works on my machine."

So the principle is simple:

> **Remove boundaries.**
> **If you cannot remove them, reduce them.**
> **If you cannot reduce them, gather them in one place.**

Incidentally, the creation of this README itself was triggered by a boundary.

The author tried to export a conversation with ChatGPT as Markdown, only to discover that Chrome could not directly save the file into the WSL Linux filesystem.

So the file traveled:

```text
ChatGPT
   |
   v
Chrome
   |
   v
C:\Temp\foobar.md
   |
   v
/mnt/c/Temp/foobar.md
   |
   v
~/tmp/foobar.md
```

The author looked upon this magnificent procession of filesystem boundaries and said:

> "Bugs grow on boundaries."

Then he added:

> "The Ministry of Education should ban Windows."

Readers are invited to evaluate the second proposition independently.

---

## Why the home directory?

Projects end.

Companies change.

Customers change.

Programming languages change.

Frameworks, if left unattended for a few years, acquire the adjective "legacy."

But:

```bash
$ cd ~
```

has remarkable staying power.

This is not where you store knowledge about **the current project**.

This is where you store knowledge about:

**how you work.**

Project-specific artifacts and your personal method of working should not be the same thing.

That is why the root of this environment is `~`.

---

## Design principles

This environment generally prefers the following principles.

1. **Build small things**
   Give one command one job.

2. **Compose**
   Prefer small parts connected by pipes and files over giant all-purpose tools.

3. **Script repetition**
   Before writing a procedure manual, ask whether you can write an executable procedure instead.

4. **Make AI a parts manufacturer**
   Do not merely delegate work to AI. Have it leave behind CLIs and scripts that can be reused next time.

5. **Cache reasoning**
   Once a decision works, preserve it as code, configuration, tests, or documentation.

6. **Reduce boundaries**
   Do not multiply conversions, wrappers, GUIs, proprietary formats, or synchronous communication without good reason.

7. **Turn failures into assets**
   If you step on a landmine once, put up a sign. Better yet, remove the landmine.

8. **Do not turn humans into machine components**
   Never implement repetitive computation using human attention when a computer can do it instead.

---

## Setup

This repository contains files that make up the author's home development environment.

**Copying the entire repository directly into your own home directory is not recommended.**

A home directory is surprisingly close to a personality.

Installing someone else's personality with:

```bash
$ cp -a someone-else/* ~/
```

rarely ends well.

Read the contents first.

Steal only what you need.

It is MIT licensed.

The theft is legal.

---

## Intended environment

The central philosophy assumes a UNIX-like environment.

In particular, this repository is designed with combinations of the following in mind:

* Linux
* WSL
* bash
* Python
* Git
* CLI-based AI agents

The specific products are not the important part.

What matters is that things can be:

**represented as text, operated through commands, and composed.**

That is the real platform.

---

## Will this repository ever be finished?

No.

This is not an application.

It is a **workshop**.

You work.

You encounter something annoying.

You think, "I never want to do that again."

You write a script.

You ask AI to improve it.

You test it.

You `git commit`.

And the workshop becomes slightly better.

Then:

```text
work
 ↓
friction
 ↓
abstraction
 ↓
script
 ↓
reuse
 ↓
harder work
 ↓
new friction
 ↓
...
```

The loop never ends.

Fortunately, as infinite loops go, this one is rather enjoyable.

---

## Finally

A good development environment is not one with the most features.

It is one in which:

**humans do not have to think about the same thing twice.**

Knowledge once acquired does not disappear.
Problems once solved do not need to be solved again.
Yesterday's self helps today's self.
Today's AI leaves tools behind for tomorrow's AI.

That is the ideal.

An IDE is not merely a screen on which you write code.

**It is a place where thought is externalized, composed, and reused.**

And if that is true:

```bash
$ pwd
/home/developer
```

then this is already an IDE.

---

> **Your home directory is an IDE.**
>
> And a good IDE gradually takes work away from the person using it.
>
> If, in the end, the human has nothing left to do, the design was a success. :-)
