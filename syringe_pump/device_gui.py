#!/usr/bin/env python3
#!/usr/bin/python
# -*- coding: utf-8 -*-

import wx
import epics
import epics.wx
from logging import debug,warn,info,error


import wx

__version__ = "0.0.0" #initial
prefix = 'NIH:SYRINGE1.'
class PanelTemplate(wx.Frame):

        title = "GUI Panel Template"

        def __init__(self):
            wx.Frame.__init__(self, None, wx.ID_ANY, title=self.title, style=wx.DEFAULT_FRAME_STYLE)
            self.panel=wx.Panel(self, -1, size = (200,75))
            self.Bind(wx.EVT_CLOSE, self.OnQuit)

            self.initialize_GUI()
            self.SetBackgroundColour(wx.Colour(255,255,255))
            self.Centre()
            self.Show()

        def OnQuit(self,event):
            """
            orderly exit of Panel if close button is pressed
            """
            self.Destroy()
            del self

        def initialize_GUI(self):
            """
            """
            sizer = wx.GridBagSizer(hgap = 5, vgap = 5)
            self.label ={}
            self.field = {}
            self.sizer = {}
            main_sizer = wx.BoxSizer(wx.VERTICAL)
            topSizer = wx.BoxSizer(wx.VERTICAL)

            self.sizer[f'{prefix}'] = wx.BoxSizer(wx.HORIZONTAL)
            self.label[f'{prefix}'] = wx.StaticText(self.panel, label= f'{prefix}', style = wx.ALIGN_CENTER)
            self.sizer[f'{prefix}'].Add(self.label[f'{prefix}'] , 0)

            self.sizer[b'RBV'] = wx.BoxSizer(wx.HORIZONTAL)
            self.label[b'RBV'] = wx.StaticText(self.panel, label= 'Volume', style = wx.ALIGN_CENTER)
            self.field[b'RBV'] = epics.wx.PVText(self.panel, pv= prefix+'RBV',minor_alarm = wx.Colour(5, 6, 7),auto_units = True)
            self.sizer[b'RBV'].Add(self.label[b'RBV'] , 0)
            self.sizer[b'RBV'].Add(self.field[b'RBV'] , 0)

            self.sizer[b'VAL'] = wx.BoxSizer(wx.HORIZONTAL)
            self.label[b'VAL'] = wx.StaticText(self.panel, label= 'Volume', style = wx.ALIGN_CENTER)
            self.field[b'VAL'] = epics.wx.PVFloatCtrl(self.panel, pv= prefix+'VAL')
            self.sizer[b'VAL'].Add(self.label[b'VAL'] , 0)
            self.sizer[b'VAL'].Add(self.field[b'VAL'] , 0)

            self.sizer[b'VELO'] = wx.BoxSizer(wx.HORIZONTAL)
            self.label[b'VELO'] = wx.StaticText(self.panel, label= 'Speed', style = wx.ALIGN_CENTER)
            self.field[b'VELO'] = epics.wx.PVFloatCtrl(self.panel, pv= prefix+'VELO')
            self.sizer[b'VELO'].Add(self.label[b'VELO'] , 0)
            self.sizer[b'VELO'].Add(self.field[b'VELO'] , 0)

            self.sizer[b'VALVE'] = wx.BoxSizer(wx.HORIZONTAL)
            self.label[b'VALVE'] = wx.StaticText(self.panel, label= 'Valve', style = wx.ALIGN_CENTER)
            self.field[b'VALVE'] = epics.wx.PVTextCtrl(self.panel, pv= prefix+'VALVE')
            self.sizer[b'VALVE'].Add(self.label[b'VALVE'] , 0)
            self.sizer[b'VALVE'].Add(self.field[b'VALVE'] , 0)

            main_sizer.Add(self.sizer[f'{prefix}'],0)
            main_sizer.Add(self.sizer[b'VAL'],0)
            main_sizer.Add(self.sizer[b'RBV'],0)
            main_sizer.Add(self.sizer[b'VELO'],0)
            main_sizer.Add(self.sizer[b'VALVE'],0)


            self.Center()
            self.Show()
            topSizer.Add(main_sizer,0)


            self.panel.SetSizer(topSizer)
            topSizer.Fit(self)
            self.Layout()
            self.panel.Layout()
            self.panel.Fit()
            self.Fit()

if __name__ == '__main__':
    from pdb import pm
    import logging
    from tempfile import gettempdir


    app = wx.App(redirect=False)
    panel = PanelTemplate()

    app.MainLoop()
