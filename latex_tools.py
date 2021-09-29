from numbers import Number
from general_utils import high_prec

class WrappedLatex:

    def __init__(self, name, cmd=None):
        self.name = name
        self.cmd = name if cmd is None else cmd

    def __get__(self, instance, cls):
        if instance is None:
            return self
        return Text._wrap_latex(self.cmd, instance.__dict__[self.name])

    def __set__(self, instance, value):
        if value is None:
            value = ''
        instance.__dict__[self.name] = value


class Text:

    _latex_cmds = {'bf': 'textbf', 'it': 'textit', 'tt': 'texttt'}


    def __init__(self, text, error=None, style_kws=None):
        self.error = error
        self.style_kws = {} if style_kws is None else style_kws
        self.text = text

        if type(error) == dict:
            self.style_kws = error


    @staticmethod
    def _parse_text_style(word):
        ret = []

        for code in ['bf', 'it', 'tt']:
            if code in word:
                ret.append(code)

        return ret

    @staticmethod
    def _wrap_latex(cmd, *text):
        if text:
            text = '{' + '}{'.join(text) + '}'
            return f'\\{cmd}{text}'
        else:
            return f'\\{cmd}'

    @staticmethod
    def _multirow_latex(title, row):
        pass

    def _infer_latex(self):
        # Figure out core latex string for the given value/error/precision

        # try:
        #     precision = self.style_kws['precision']
        # except KeyError:
        #     precision = None
        #
        # scientific = self.style_kws.get('scientific')
        # use_scientific = True if scientific is not None else False
        # code = 'f' if not scientific else 'e'
        #
        # if precision is not None:
        #     try:
        #         if not isinstance(self.text, int):
        #             if use_scientific:
        #                 text = high_prec(self.text, precision)
        #             else:
        #                 text = f'{self.text:.{precision}{code}}'
        #         else:
        #             text = self.text
        #         if self.error is not None:
        #             if use_scientific:
        #                 error = high_prec(self.error, precision)
        #             else:
        #                 error = f'{self.error:.{precision}{code}}'
        #     except (TypeError, ValueError):
        #         text = self.text
        #         error = self.error
        # else:
        #     text = self.text
        #     error = self.error
        #
        # # Check if error is 0, then replace with "~0"
        # try:
        #     if error is not None:
        #         test_error = error.replace('.', '0')
        #         if all(map(lambda x: x=='0', test_error)):
        #             error = r'\sim 0'
        # except UnboundLocalError:
        #     pass

        fmt = self.style_kws.get("fmt")

        is_str = type(self.text) == str
        has_error = self.error is not None

        if has_error:
            from uncertainties import ufloat
            text = ufloat(self.text, self.error)


        if fmt is not None and not is_str:

            if "s" in fmt:
                import re
                prec = re.match(r'\d', fmt).group()
                text = high_prec(self.text, prec=prec)
                if has_error:
                    error = high_prec(self.error, prec=prec)

            else:
                if has_error:
                    text = format(text, fmt+'L')

                else:
                    text = format(self.text, fmt)

        else:
            text = self.text


        ret = self.text if is_str else f'${text}$'

        return ret

    
    def _apply_fmt(self):
        # Apply formatting arguments supplies in style_kws

        text = self._infer_latex()

        ret = []

        for option in 'cell_color text_size text_style text_color'.split():
            try:
                setting = self.style_kws[option]
            except KeyError:
                continue
            
            if option == 'cell_color':
                ret.append(Text._wrap_latex('cellcolor', setting))

            elif option == 'text_size':
                ret.append(Text._wrap_latex(setting + ' '))

            elif option == 'text_style':
                for sty in Text._parse_text_style(setting):
                    if sty == 'bf' and '$' in text:
                        text = '\\boldmath ' + text + ' \\unboldmath'
                    else:
                        text = Text._wrap_latex(Text._latex_cmds[sty], text)

            elif option == 'text_color':
                ret.append(Text._wrap_latex('textcolor', setting, text))


        ret = ''.join(ret)
        if text not in ret:
            ret = ret + text
        else:
            pass

        try:
            n_rows = self.style_kws['multirow']
        except KeyError:
            n_rows = None

        try:
            n_cols = self.style_kws['multicol']
        except KeyError:
            n_cols = None

        if n_rows is not None:
            return f'\\multirow{{{n_rows}}}{{*}}{{{ret}}}'
        elif n_cols is not None:
            # return f'\\multicolumn{{{n_cols}}}{{|c|}}{{{ret}}}'
            return f'\\multicolumn{{{n_cols}}}{{c}}{{{ret}}}'
        else:
            return ret

    @property
    def latex(self):
        # Text getter logic to format LaTeX
        return self._apply_fmt()
    
    def __repr__(self):
        return f'Text({self.text}, {self.error}, {self.style_kws})'


class Table:

    caption = WrappedLatex('caption')
    label = WrappedLatex('label')

    def __init__(self, caption=None, label=None, columns=None, centering=True, ana_style=True, location='H',
                 size=None, vspace="0mm", hspace="0mm", align='l'):
        self.caption = caption
        self.label = label
        self._original_cols = columns
        self.centering = centering
        self.ana_style = ana_style
        self.location = location
        self.size = size
        self.vspace = vspace
        self.hspace = hspace
        self.align = align

        self.columns = columns

        self.row_number = (x for x in range(9999))
        self.cline_start = 2  # For multirows

    @property
    def columns(self):
        return self._columns
    
    @columns.setter
    def columns(self, value):

        def _has_label(word):
            if ':=' in word:
                return word.split(':=')
            else:
                return word, word


        if value is not None:

            # Handling for multicolumns
            title_row = []
            titles = []
            for title in value:
                main_title, *subtitles = title.split('::')
                nsub = len(subtitles)
                main_title, main_title_label = _has_label(main_title)
                subtitles_, subtitle_labels = [], []
                for st in subtitles:
                    st_, stl = _has_label(st)
                    subtitles_.append(st_)
                    subtitle_labels.append(stl)

                title_row.append((main_title, subtitles_))  # Keep track of subcolumn children so latex can be generated properly

                # One can encode a custom title name instead of something more complex, for adding values later with kwargs:
                #  e.g.:   table.columns = ['Bachelor:=bach', 'Magnet Polarity:=mag']
                # Same can also be done for subcolumn declarations:
                #  e.g.:   table.columns = ['Magnet Polarity::Up:=up::Down:=down',]

                if nsub > 0:
                    titles += subtitle_labels
                else:
                    titles.append(main_title_label)

            # self._columns = {k: [] for k in value}
            self._title_row = title_row
            self._ntitles = len(titles)
            self._columns = {k: [] for k in titles}

    @staticmethod
    def _val_to_text(value):
        if isinstance(value, Text):
            return value

        else:
            try:
                # When error/style comes bundled with value in a tuple
                if type(value) == str:
                    raise TypeError  # Don't unpack strings!
                
                # If a dict is supplied but no error term, set error to be None
                if len(value) == 2 and type(value[-1]) == dict:
                    value = (value[0], None, value[1])

                value = Text(*value)

            except TypeError:
                # For a single literal value, e.g. string or int
                value = Text(value)

            return value

    def set_cell_val(self, column, kwargs, style_kws=None):
        if style_kws is None:
            style_kws = {}

        try:
            value = kwargs.pop(column)
        except KeyError:
            value = Text('{}', style_kws=style_kws)

        value = self._give_style(value, style_kws=style_kws)
        value = self._val_to_text(value)
        if value.style_kws == {}:
            value.style_kws = style_kws

        self.columns[column].append(value)

    def _add_row(self, kwargs, multirow=False):
        try:
            style_kws = kwargs.pop('style_kws')

        except KeyError:
            style_kws = {}

        for i, column in enumerate(self.columns):
            if multirow and i==0:
                temp_style_kws = {}
            else:
                temp_style_kws = dict(style_kws)
                
            self.set_cell_val(column, kwargs, temp_style_kws)

    @staticmethod
    def _give_style(value, error=None, style_kws=None):
        if style_kws is None:
            style_kws = {}

        if isinstance(value, Text):
            return value

        # Checks if value has error or style_kws terms, and supplies defaults if not
        if isinstance(value, (tuple, list)):
            if len(value) == 1:
                value = [*value, error, style_kws]  # No error term

            elif len(value) == 2:
                value = [*value, style_kws]

            elif len(value) == 3:
                value = value

            else:
                raise TypeError('Value must have 1, 2 or 3 terms in tuple, or be a literal. Not {value}')

        else:
            value = [value, None, style_kws]
        
        return value

    def add_row(self, **kwargs):
        # One can set a style option for the entire row if this is desired:
        try:
            row_style_kws = dict(kwargs.pop('style_kws'))
        except KeyError:
            row_style_kws = {}

        keys = list(kwargs.keys())
        has_subrows = 'subrows' in keys

        # Convert all values provided into Text objects, including subrows [{...}, {...}, ...] arguments
        for key in keys:

            value = kwargs[key]

            if key != 'subrows':
                kwargs.update({key: self._val_to_text(value)})

            else:
                prev_key = keys[keys.index(key) - 1]
                kwargs[prev_key].style_kws.update({'multirow': len(kwargs[key])})
                for i, row in enumerate(kwargs[key]):
                    for key_ in row:
                        if key_ == 'style_kws':
                            continue
                        kwargs[key][i].update({key_: self._val_to_text(row[key_])})


        # Handling for multi-row
        if has_subrows:
            kwargs = {**kwargs, **kwargs['subrows'].pop(0)}

            try:
                temp_style_kws = kwargs.pop('style_kws')

            except KeyError:
                temp_style_kws = dict(row_style_kws)

            kwargs = {**kwargs, 'style_kws': temp_style_kws}
        
        else:
            kwargs['style_kws'] = dict(row_style_kws)

        self._add_row(kwargs)

        if has_subrows:
            for row in kwargs['subrows']:
                try:
                    temp_style_kws = row.pop('style_kws')
                except KeyError:
                    temp_style_kws = dict(row_style_kws)

                row = {**row, 'style_kws': temp_style_kws}
                self._add_row(row, multirow=True)

    @property
    def subtitle_row(self):
        ret = []

        for _, subs in self._title_row:
            nsubs = len(subs)
            if nsubs > 0:
                ret += subs
            else:
                # ret.append(Text('{}', style_kws={'cell_color': 'Black!10'}))
                ret.append(Text('{}'))

        if any([x.text != '{}' for x in ret if isinstance(x, Text)]) or any([x for x in ret if not isinstance(x, Text)]):
            return [self._val_to_text(x) for x in ret]
    
    @property
    def preamble(self):
        side_caps = '' if self.ana_style else '|'
        ret = '\\begin{table}[' + self.location + ']\n' + ('\\centering\n' if self.centering else '')
        ret += f'\\{self.size}\n' if self.size is not None else ''
        ret += '\n'.join([self.caption, self.label]) + '\n'
        ret += f'\\hspace*{{{self.hspace}}}\n'
        ret += f'\\vspace*{{{self.vspace}}}\n'
        ret += '\\begin{tabular}{' + f'{side_caps}{self.align}'*self._ntitles + side_caps +'}\n'
        return ret

    def summarize(self, options, columns='all', style_kws=None, mean_name=None, std_name=None):
        import numpy as np

        if mean_name is None:
            mean_name = 'Mean'

        if std_name is None:
            std_name = '$\\sigma$'

        if columns == 'all':
            index, *columns = list(self.columns)

        if style_kws is None:
            style_kws = {'precision': 3}

        means, stds = {}, {}

        for column in columns:
            data = [float(x.text) for x in self.columns[column] if isinstance(x.text, Number)]
            means[column] = (np.mean(data), style_kws)
            stds[column] = (np.std(data), style_kws)

        self.add_row(**{index: mean_name, **means})
        self.add_row(**{index: std_name, **stds})

        # old_cols = dict(self.columns)
        # self.columns = [':=dummy', *self._original_cols]

        # nrows = len(list(old_cols.values())[0])

        # old_cols['dummy'] = [Text('') for _ in range(nrows)]

        # self.columns.update(old_cols)

        # self.add_row(dummy='Mean', **means)
        # self.add_row(dummy='Std. dev.', **stds)

        # Assume left-most column is an index of some kind
        self.add_row

    def highlight(self, axis, style=None, fn=max):

        if style is None:
            style = dict(cell_color="Red!10")

        if axis == "column" or axis == 1:

            for ii, (_, row) in enumerate(self.columns.items()):

                if ii == 0:
                    continue

                _, i = fn((x.text, i) for i, x in enumerate(row))
                row[i].style_kws.update(style)

        else:
            raise NotImplementedError

    @property
    def n_rows(self):
        return len(list(self.columns.values())[0])

    @property
    def latex(self):
        ret = self.preamble
        ret += '\\hline' + ('\\hline\n' if self.ana_style else '\n')

        rows = []

        has_subcols = False

        # Make the title row
        row = []
        for title, subs in self._title_row:
            nsubs = len(subs)
            if nsubs == 0:
                row.append(self._val_to_text(title).latex)
            else:
                has_subcols = True
                text = self._val_to_text(title)
                text.style_kws['multicol'] = nsubs 
                row.append(text.latex)
        rows.append(row)

        # Make subtitle row, if needed
        subtitles = self.subtitle_row
        if subtitles is not None:
            subtitles = list(map(lambda x: x.latex, subtitles))
            rows.append(subtitles)

        # Make the main body
        for i in range(self.n_rows):
            row = []

            for title in self.columns:
                row.append(self.columns[title][i].latex)

            rows.append(row)

        # TODO: replace this with a class implementation which can hold hline information
        for row in rows:
            if  'multirow' in row[0]:
                row.append({'cline': f'{{{self.cline_start}-{self._ntitles}}}'})
            else:
                row.append({'hline': 1})
        

        join_strs = []
        for i, row in enumerate(rows):
            is_title_row = i == 0
            is_subtitle_row = i == 1 and has_subcols

            cmd = list(row[-1].keys())[0]
            if cmd == 'cline':
                opt = '\\cline' + list(row[-1].values())[0]
            else:
                line = '' if self.ana_style else '\\hline'
                if is_title_row or is_subtitle_row:
                    line = '\\hline'


                opt = line * list(row[-1].values())[0]

            join_strs.append('\\\\ ' + opt + '\n')

        body = ''
        for row, join_str in zip(rows, join_strs):
            body += ' & '.join(row[:-1]) + join_str

        # ret += ' \\\\ \\hline \n '.join(rows) + ' \\\\ \\hline \n'
        ret += body
        if self.ana_style:
            ret += '\\hline\\hline'
        ret += '\\end{tabular}\n'
        # ret += '\n'.join([self.caption, self.label]) + '\n'
        ret += '\\end{table}\n'

        return ret

    def save(self, path, mode='w'):
        with open(path, mode) as f:
            f.write(self.latex)
          

