# Copyright (c) 2012-2015 Tycho Andersen
# Copyright (c) 2013 xarvh
# Copyright (c) 2013 horsik
# Copyright (c) 2013-2014 roger
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from . import command
from . import hook
from . import utils
from . import xcbq

from six import MAXSIZE
import warnings


class Key(object):
    """Defines a keybinding.

    Parameters
    ==========
    modifiers:
        A list of modifier specifications. Modifier specifications are one of:
        "shift", "lock", "control", "mod1", "mod2", "mod3", "mod4", "mod5".
    key:
        A key specification, e.g. "a", "Tab", "Return", "space".
    commands:
        A list of lazy command objects generated with the command.lazy helper.
        If multiple Call objects are specified, they are run in sequence.
    kwds:
        A dictionary containing "desc", allowing a description to be added
    """
    def __init__(self, modifiers, key, *commands, **kwds):
        self.modifiers = modifiers
        self.key = key
        self.commands = commands
        self.desc = kwds.get("desc", "")
        if key not in xcbq.keysyms:
            raise utils.QtileError("Unknown key: %s" % key)
        self.keysym = xcbq.keysyms[key]
        try:
            self.modmask = utils.translate_masks(self.modifiers)
        except KeyError as v:
            raise utils.QtileError(v)

    def __repr__(self):
        return "<Key (%s, %s)>" % (self.modifiers, self.key)


class Drag(object):
    """Defines binding of a mouse to some dragging action

    On each motion event command is executed with two extra parameters added x
    and y offset from previous move

    It focuses clicked window by default.  If you want to prevent it pass,
    `focus=None` as an argument
    """
    def __init__(self, modifiers, button, *commands, **kwargs):
        self.start = kwargs.get("start")
        self.focus = kwargs.get("focus", "before")
        self.modifiers = modifiers
        self.button = button
        self.commands = commands
        try:
            self.button_code = int(self.button.replace('Button', ''))
            self.modmask = utils.translate_masks(self.modifiers)
        except KeyError as v:
            raise utils.QtileError(v)

    def __repr__(self):
        return "<Drag (%s, %s)>" % (self.modifiers, self.button)


class Click(object):
    """Defines binding of a mouse click

    It focuses clicked window by default.  If you want to prevent it, pass
    `focus=None` as an argument
    """
    def __init__(self, modifiers, button, *commands, **kwargs):
        self.focus = kwargs.get("focus", "before")
        self.modifiers = modifiers
        self.button = button
        self.commands = commands
        try:
            self.button_code = int(self.button.replace('Button', ''))
            self.modmask = utils.translate_masks(self.modifiers)
        except KeyError as v:
            raise utils.QtileError(v)

    def __repr__(self):
        return "<Click (%s, %s)>" % (self.modifiers, self.button)


class EzConfig(object):
    """
    Helper class for defining key and button bindings in an emacs-like format.
    Inspired by Xmonad's XMonad.Util.EZConfig.
    """

    modifier_keys = {
        'M': 'mod4',
        'A': 'mod1',
        'S': 'shift',
        'C': 'control',
    }

    def parse(self, spec):
        """
        Splits an emacs keydef into modifiers and keys. For example:
          "M-S-a"     -> ['mod4', 'shift'], 'a'
          "A-<minus>" -> ['mod1'], 'minus'
          "C-<Tab>"   -> ['control'], 'Tab'
        """
        mods = []
        keys = []

        for key in spec.split('-'):
            if not key:
                break
            if key in self.modifier_keys:
                if keys:
                    msg = 'Modifiers must always come before key/btn: %s'
                    raise utils.QtileError(msg % spec)
                mods.append(self.modifier_keys[key])
                continue
            if len(key) == 1:
                keys.append(key)
                continue
            if len(key) > 3 and key[0] == '<' and key[-1] == '>':
                keys.append(key[1:-1])
                continue

        if not keys:
            msg = 'Invalid key/btn specifier: %s'
            raise utils.QtileError(msg % spec)

        if len(keys) > 1:
            msg = 'Key chains are not supported: %s' % spec
            raise utils.QtileError(msg)

        return mods, keys[0]

class EzKey(EzConfig, Key):
    def __init__(self, keydef, *commands):
        modkeys, key = self.parse(keydef)
        super(EzKey, self).__init__(modkeys, key, *commands)

class EzClick(EzConfig, Click):
    def __init__(self, btndef, *commands, **kwargs):
        modkeys, button = self.parse(btndef)
        button = 'Button%s' % button
        super(EzClick, self).__init__(modkeys, button, *commands, **kwargs)

class EzDrag(EzConfig, Drag):
    def __init__(self, btndef, *commands, **kwargs):
        modkeys, button = self.parse(btndef)
        button = 'Button%s' % button
        super(EzDrag, self).__init__(modkeys, button, *commands, **kwargs)


class ScreenRect(object):

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __repr__(self):
        return '<%s %d,%d %d,%d>' % (
            self.__class__.__name__,
            self.x, self.y,
            self.width, self.height
        )

    def hsplit(self, columnwidth):
        assert columnwidth > 0
        assert columnwidth < self.width
        return (
            self.__class__(self.x, self.y, columnwidth, self.height),
            self.__class__(
                self.x + columnwidth, self.y,
                self.width - columnwidth, self.height
            )
        )

    def vsplit(self, rowheight):
        assert rowheight > 0
        assert rowheight < self.height
        return (
            self.__class__(self.x, self.y, self.width, rowheight),
            self.__class__(
                self.x, self.y + rowheight,
                self.width, self.height - rowheight
            )
        )


class Screen(command.CommandObject):
    """A physical screen, and its associated paraphernalia.

    Define a screen with a given set of Bars of a specific geometry.  Note that
    bar.Bar objects can only be placed at the top or the bottom of the screen
    (bar.Gap objects can be placed anywhere).  Also, ``x``, ``y``, ``width``,
    and ``height`` aren't specified usually unless you are using 'fake
    screens'.

    Parameters
    ==========
    top: List of Gap/Bar objects, or None.
    bottom: List of Gap/Bar objects, or None.
    left: List of Gap/Bar objects, or None.
    right: List of Gap/Bar objects, or None.
    x : int or None
    y : int or None
    width : int or None
    height : int or None
    """
    def __init__(self, top=None, bottom=None, left=None, right=None,
                 x=None, y=None, width=None, height=None):
        self.group = None
        self.previous_group = None

        self.top = top
        self.bottom = bottom
        self.left = left
        self.right = right
        self.qtile = None
        self.index = None
        # x position of upper left corner can be > 0
        # if one screen is "right" of the other
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def _configure(self, qtile, index, x, y, width, height, group):
        self.qtile = qtile
        self.index = index
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.setGroup(group)
        for i in self.gaps:
            i._configure(qtile, self)

    @property
    def gaps(self):
        return (i for i in [self.top, self.bottom, self.left, self.right] if i)

    @property
    def dx(self):
        return self.x + self.left.size if self.left else self.x

    @property
    def dy(self):
        return self.y + self.top.size if self.top else self.y

    @property
    def dwidth(self):
        val = self.width
        if self.left:
            val -= self.left.size
        if self.right:
            val -= self.right.size
        return val

    @property
    def dheight(self):
        val = self.height
        if self.top:
            val -= self.top.size
        if self.bottom:
            val -= self.bottom.size
        return val

    def get_rect(self):
        return ScreenRect(self.dx, self.dy, self.dwidth, self.dheight)

    def setGroup(self, new_group, save_prev=True):
        """Put group on this screen"""
        if new_group.screen == self:
            return

        if save_prev:
            self.previous_group = self.group

        if new_group is None:
            return

        if new_group.screen:
            # g1 <-> s1 (self)
            # g2 (new_group) <-> s2 to
            # g1 <-> s2
            # g2 <-> s1
            g1 = self.group
            s1 = self
            g2 = new_group
            s2 = new_group.screen

            s2.group = g1
            g1._setScreen(s2)
            s1.group = g2
            g2._setScreen(s1)
        else:
            old_group = self.group
            self.group = new_group

            # display clients of the new group and then hide from old group
            # to remove the screen flickering
            new_group._setScreen(self)

            if old_group is not None:
                old_group._setScreen(None)

        hook.fire("setgroup")
        hook.fire("focus_change")
        hook.fire(
            "layout_change",
            self.group.layouts[self.group.currentLayout],
            self.group
        )

    def _items(self, name):
        if name == "layout":
            return (True, list(range(len(self.group.layouts))))
        elif name == "window":
            return (True, [i.window.wid for i in self.group.windows])
        elif name == "bar":
            return (False, [x.position for x in self.gaps])

    def _select(self, name, sel):
        if name == "layout":
            if sel is None:
                return self.group.layout
            else:
                return utils.lget(self.group.layouts, sel)
        elif name == "window":
            if sel is None:
                return self.group.currentWindow
            else:
                for i in self.group.windows:
                    if i.window.wid == sel:
                        return i
        elif name == "bar":
            return getattr(self, sel)

    def resize(self, x=None, y=None, w=None, h=None):
        x = x or self.x
        y = y or self.y
        w = w or self.width
        h = h or self.height
        self._configure(self.qtile, self.index, x, y, w, h, self.group)
        for bar in [self.top, self.bottom, self.left, self.right]:
            if bar:
                bar.draw()
        self.qtile.call_soon(self.group.layoutAll)

    def cmd_info(self):
        """
            Returns a dictionary of info for this screen.
        """
        return dict(
            index=self.index,
            width=self.width,
            height=self.height,
            x=self.x,
            y=self.y
        )

    def cmd_resize(self, x=None, y=None, w=None, h=None):
        """Resize the screen"""
        self.resize(x, y, w, h)

    def cmd_next_group(self, skip_empty=False, skip_managed=False):
        """Switch to the next group"""
        n = self.group.nextGroup(skip_empty, skip_managed)
        self.setGroup(n)
        return n.name

    def cmd_prev_group(self, skip_empty=False, skip_managed=False):
        """Switch to the previous group"""
        n = self.group.prevGroup(skip_empty, skip_managed)
        self.setGroup(n)
        return n.name

    def cmd_toggle_group(self, group_name=None):
        """Switch to the selected group or to the previously active one"""
        group = self.qtile.groupMap.get(group_name)
        if group in (self.group, None):
            group = self.previous_group
        self.setGroup(group)

    def cmd_togglegroup(self, groupName=None):
        """Switch to the selected group or to the previously active one

        Deprecated: use toggle_group()"""
        warnings.warn("togglegroup is deprecated, use toggle_group", DeprecationWarning)
        self.cmd_toggle_group(groupName)


class Group(object):
    """Represents a "dynamic" group

    These groups can spawn apps, only allow certain Matched windows to be on
    them, hide when they're not in use, etc.
    Groups are identified by their name.

    Parameters
    ==========
    name : string
        the name of this group
    matches : default ``None``
        list of ``Match`` objects whose  windows will be assigned to this group
    exclusive : boolean
        when other apps are started in this group, should we allow them here or not?
    spawn : string or list of strings
        this will be ``exec()`` d when the group is created, you can pass
        either a program name or a list of programs to ``exec()``
    layout : string
        the name of default layout for this group (e.g. 'max' or 'stack').
        This is the name specified for a particular layout in config.py
        or if not defined it defaults in general the class name in all lower case.
    layouts : list
        the group layouts list overriding global layouts.
        Use this to define a separate list of layouts for this particular group.
    persist : boolean
        should this group stay alive with no member windows?
    init : boolean
        is this group alive when qtile starts?
    position : int
        group position
    label : string
        the display name of the group.
        Use this to define a display name other than name of the group.
        If set to None, the display name is set to the name.
    """
    def __init__(self, name, matches=None, exclusive=False,
                 spawn=None, layout=None, layouts=None, persist=True, init=True,
                 layout_opts=None, screen_affinity=None, position=MAXSIZE,
                 label=None):
        self.name = name
        self.label = label
        self.exclusive = exclusive
        self.spawn = spawn
        self.layout = layout
        self.layouts = layouts or []
        self.persist = persist
        self.init = init
        self.matches = matches or []
        self.layout_opts = layout_opts or {}

        self.screen_affinity = screen_affinity
        self.position = position

    def __repr__(self):
        attrs = utils.describe_attributes(self,
            ['exclusive', 'spawn', 'layout', 'layouts', 'persist', 'init',
            'matches', 'layout_opts', 'screen_affinity'])
        return '<config.Group %r (%s)>' % (self.name, attrs)


class Match(object):
    """Match for dynamic groups

    It can match by title, class or role.

    ``Match`` supports both regular expression objects (i.e. the result of
    ``re.compile()``) or strings (match as a "include" match). If a window
    matches any of the things in any of the lists, it is considered a match.

    Parameters
    ==========
    title:
        things to match against the title (WM_NAME)
    wm_class:
        things to match against the second string in WM_CLASS atom
    role:
        things to match against the WM_ROLE atom
    wm_type:
        things to match against the WM_TYPE atom
    wm_instance_class:
        things to match against the first string in WM_CLASS atom
    net_wm_pid:
        things to match against the _NET_WM_PID atom (only int allowed in this
        rule)
    """
    def __init__(self, title=None, wm_class=None, role=None, wm_type=None,
                 wm_instance_class=None, net_wm_pid=None):
        if not title:
            title = []
        if not wm_class:
            wm_class = []
        if not role:
            role = []
        if not wm_type:
            wm_type = []
        if not wm_instance_class:
            wm_instance_class = []
        if not net_wm_pid:
            net_wm_pid = []

        try:
            net_wm_pid = list(map(int, net_wm_pid))
        except ValueError:
            error = 'Invalid rule for net_wm_pid: "%s" '\
                    'only ints allowed' % str(net_wm_pid)
            raise utils.QtileError(error)

        self._rules = [('title', t) for t in title]
        self._rules += [('wm_class', w) for w in wm_class]
        self._rules += [('role', r) for r in role]
        self._rules += [('wm_type', r) for r in wm_type]
        self._rules += [('wm_instance_class', w) for w in wm_instance_class]
        self._rules += [('net_wm_pid', w) for w in net_wm_pid]

    def compare(self, client):
        for _type, rule in self._rules:
            if _type == "net_wm_pid":
                def match_func(value):
                    return rule == value
            else:
                match_func = getattr(rule, 'match', None) or \
                    getattr(rule, 'count')

            if _type == 'title':
                value = client.name
            elif _type == 'wm_class':
                value = None
                _value = client.window.get_wm_class()
                if _value and len(_value) > 1:
                    value = _value[1]
            elif _type == 'wm_instance_class':
                value = client.window.get_wm_class()
                if value:
                    value = value[0]
            elif _type == 'wm_type':
                value = client.window.get_wm_type()
            elif _type == 'net_wm_pid':
                value = client.window.get_net_wm_pid()
            else:
                value = client.window.get_wm_window_role()

            if value and match_func(value):
                return True
        return False

    def map(self, callback, clients):
        """Apply callback to each client that matches this Match"""
        for c in clients:
            if self.compare(c):
                callback(c)

    def __repr__(self):
        return '<Match %s>' % self._rules


class Rule(object):
    """How to act on a Match

    A Rule contains a Match object, and a specification about what to do when
    that object is matched.

    Parameters
    ==========
    match :
        ``Match`` object associated with this ``Rule``
    float :
        auto float this window?
    intrusive :
        override the group's exclusive setting?
    break_on_match :
        Should we stop applying rules if this rule is matched?
    """
    def __init__(self, match, group=None, float=False, intrusive=False,
                 break_on_match=True):
        self.match = match
        self.group = group
        self.float = float
        self.intrusive = intrusive
        self.break_on_match = break_on_match

    def matches(self, w):
        return self.match.compare(w)

    def __repr__(self):
        actions = utils.describe_attributes(self, ['group', 'float',
            'intrusive', 'break_on_match'])
        return '<Rule match=%r actions=(%s)>' % (self.match, actions)
