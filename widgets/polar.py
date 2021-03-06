# -*- coding: utf-8 -*-

#    Copyright (C) 2010 Jeremy S. Sanders
#    Email: Jeremy Sanders <jeremy@jeremysanders.net>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
##############################################################################

"""Polar plot widget."""

import numpy as N

from nonorthgraph import NonOrthGraph
from axisticks import AxisTicks
import axis

import veusz.qtall as qt4
import veusz.document as document
import veusz.setting as setting
import veusz.utils as utils

def _(text, disambiguation=None, context='Polar'):
    """Translate text."""
    return unicode( 
        qt4.QCoreApplication.translate(context, text, disambiguation))

class Tick(setting.Line):
    '''Polar tick settings.'''

    def __init__(self, name, **args):
        setting.Line.__init__(self, name, **args)
        self.add( setting.DistancePt( 'length',
                                      '6pt',
                                      descr = _('Length of major ticks'),
                                      usertext=_('Length') ) )
        self.add( setting.Int( 'number',
                               6,
                               descr = _('Number of major ticks to aim for'),
                               usertext=_('Number')) )
        self.add( setting.Bool('hidespokes', False,
                               descr = _('Hide radial spokes'),
                               usertext = _('Hide spokes')) )
        self.add( setting.Bool('hideannuli', False,
                               descr = _('Hide annuli'),
                               usertext = _('Hide annuli') ) )
        self.get('color').newDefault('grey')

    def getLength(self, painter):
        '''Return tick length in painter coordinates'''
        
        return self.get('length').convert(painter)

class TickLabel(axis.TickLabel):
    """For tick label."""
    def __init__(self, *args, **argsv):
        axis.TickLabel.__init__(self, *args, **argsv)
        self.remove('offset')
        self.remove('rotate')
        self.remove('hide')
        self.add( setting.Bool('hideradial', False,
                               descr = _('Hide radial labels'),
                               usertext=_('Hide radial') ) )
        self.add( setting.Bool('hidetangential', False,
                               descr = _('Hide tangential labels'),
                               usertext=_('Hide tangent') ) )

class Polar(NonOrthGraph):
    '''Polar plotter.'''

    typename='polar'
    allowusercreation = True
    description = _('Polar graph')

    def __init__(self, parent, name=None):
        '''Initialise polar plot.'''
        NonOrthGraph.__init__(self, parent, name=name)
        if type(self) == NonOrthGraph:
            self.readDefaults()

    @classmethod
    def addSettings(klass, s):
        '''Construct list of settings.'''
        NonOrthGraph.addSettings(s)

        s.add( setting.FloatOrAuto('minradius', 'Auto',
                                   descr=_('Minimum value of radius'),
                                   usertext=_('Min radius')) )
        s.add( setting.FloatOrAuto('maxradius', 'Auto',
                                   descr=_('Maximum value of radius'),
                                   usertext=_('Max radius')) )
        s.add( setting.Choice('units',
                              ('degrees', 'radians'), 
                              'degrees', 
                              descr = _('Angular units'),
                              usertext=_('Units')) )
        s.add( setting.Choice('direction',
                              ('clockwise', 'anticlockwise'),
                              'anticlockwise',
                              descr = _('Angle direction'),
                              usertext = _('Direction')) )
        s.add( setting.Choice('position0',
                              ('right', 'top', 'left', 'bottom'),
                              'right',
                              descr = _('Direction of 0 angle'),
                              usertext = _(u'Position of 0°')) )
        s.add( setting.Bool('log', False,
                            descr = _('Logarithmic radial axis'),
                            usertext = _('Log')) )

        s.add( TickLabel('TickLabels', descr = _('Tick labels'),
                    usertext=_('Tick labels')),
               pixmap='settings_axisticklabels' )
        s.add( Tick('Tick', descr = _('Tick line'),
                    usertext=_('Tick')),
               pixmap='settings_axismajorticks' )

        s.get('leftMargin').newDefault('1cm')
        s.get('rightMargin').newDefault('1cm')
        s.get('topMargin').newDefault('1cm')
        s.get('bottomMargin').newDefault('1cm')

    def coordRanges(self):
        '''Get ranges of coordinates.'''
        angularrange = [[0., 2.*N.pi], [0., 360]][
            self.settings.units == 'degrees' ]
        return [
            [self._minradius, self._maxradius],
            angularrange
            ]

    def toPlotAngle(self, angles):
        """Convert one or more angles to angle on plot."""
        s = self.settings

        # unit conversion
        if s.units == 'degrees':
            angles = angles * (N.pi/180.)
        # change direction
        if self.settings.direction == 'anticlockwise':
            angles = -angles
        # add offset
        angles -= {'right': 0, 'top': 0.5*N.pi, 'left': N.pi,
                   'bottom': 1.5*N.pi}[self.settings.position0]
        return angles

    def toPlotRadius(self, radii):
        """Convert radii to a plot radii."""
        if self.settings.log:
            logmin = N.log(self._minradius)
            logmax = N.log(self._maxradius)
            r = ( N.log(N.clip(radii, 1e-99, 1e99)) - logmin ) / (
                logmax - logmin)
        else:
            r = (radii - self._minradius) / (
                self._maxradius - self._minradius)
        return N.where(r > 0., r, 0.)

    def graphToPlotCoords(self, coorda, coordb):
        '''Convert coordinates in r, theta to x, y.'''

        ca = self.toPlotRadius(coorda)
        cb = self.toPlotAngle(coordb)

        x = self._xc + ca * N.cos(cb) * self._xscale
        y = self._yc + ca * N.sin(cb) * self._yscale
        return x, y

    def drawFillPts(self, painter, extfill, cliprect,
                    ptsx, ptsy):
        '''Draw points for plotting a fill.'''
        pts = qt4.QPolygonF()
        utils.addNumpyToPolygonF(pts, ptsx, ptsy)

        filltype = extfill.filltype
        if filltype == 'center':
            pts.append( qt4.QPointF(self._xc, self._yc) )
            utils.brushExtFillPolygon(painter, extfill, cliprect, pts)
        elif filltype == 'outside':
            pp = qt4.QPainterPath()
            pp.moveTo(self._xc, self._yc)
            pp.arcTo(cliprect, 0, 360)
            pp.addPolygon(pts)
            utils.brushExtFillPath(painter, extfill, pp)
        elif filltype == 'polygon':
            utils.brushExtFillPolygon(painter, extfill, cliprect, pts)

    def drawGraph(self, painter, bounds, datarange, outerbounds=None):
        '''Plot graph area and axes.'''

        s = self.settings
        if s.maxradius == 'Auto':
            self._maxradius = datarange[1]
        else:
            self._maxradius = s.maxradius
        if s.minradius == 'Auto':
            if s.log:
                if datarange[0] > 0.:
                    self._minradius = datarange[0]
                else:
                    self._minradius = self._maxradius / 100.
            else:
                self._minradius = 0.
        else:
            self._minradius = s.minradius

        # stop negative values
        if s.log:
            self._minradius = N.clip(self._minradius, 1e-99, 1e99)
            self._maxradius = N.clip(self._maxradius, 1e-99, 1e99)
        if self._minradius == self._maxradius:
            self._maxradius = self._minradius + 1

        self._xscale = (bounds[2]-bounds[0])*0.5
        self._yscale = (bounds[3]-bounds[1])*0.5
        self._xc = 0.5*(bounds[0]+bounds[2])
        self._yc = 0.5*(bounds[3]+bounds[1])

        path = qt4.QPainterPath()
        path.addEllipse( qt4.QRectF( qt4.QPointF(bounds[0], bounds[1]),
                                     qt4.QPointF(bounds[2], bounds[3]) ) )
        utils.brushExtFillPath(painter, s.Background, path,
                               stroke=s.Border.makeQPenWHide(painter))

    def setClip(self, painter, bounds):
        '''Set clipping for graph.'''
        p = qt4.QPainterPath()
        p.addEllipse( qt4.QRectF( qt4.QPointF(bounds[0], bounds[1]),
                                  qt4.QPointF(bounds[2], bounds[3]) ) )
        painter.setClipPath(p)

    def drawAxes(self, painter, bounds, datarange, outerbounds=None):
        '''Plot axes.'''

        s = self.settings
        t = s.Tick

        atick = AxisTicks(self._minradius, self._maxradius,
                          t.number, t.number*4,
                          extendmin=False, extendmax=False,
                          logaxis=s.log)
        atick.getTicks()
        majtick = atick.tickvals

        # drop 0 at origin
        if self._minradius == 0. and not s.log:
            majtick = majtick[1:]

        # draw ticks as circles
        if not t.hideannuli:
            painter.setPen( s.Tick.makeQPenWHide(painter) )
            painter.setBrush( qt4.QBrush() )      

            for tick in majtick:
                radius = self.toPlotRadius(tick)
                if radius > 0:
                    rect = qt4.QRectF(
                        qt4.QPointF( self._xc - radius*self._xscale,
                                     self._yc - radius*self._yscale ),
                        qt4.QPointF( self._xc + radius*self._xscale,
                                     self._yc + radius*self._yscale ) )
                    painter.drawEllipse(rect)

        # setup axes plot
        tl = s.TickLabels
        scale, format = tl.scale, tl.format
        if format == 'Auto':
            format = atick.autoformat
        painter.setPen( tl.makeQPen() )
        font = tl.makeQFont(painter)

        # draw radial axis
        if not s.TickLabels.hideradial:
            for tick in majtick:
                num = utils.formatNumber(tick*scale, format,
                                         locale=self.document.locale)
                x = self.toPlotRadius(tick) * self._xscale + self._xc
                r = utils.Renderer(painter, font, x, self._yc, num,
                                   alignhorz=-1,
                                   alignvert=-1, usefullheight=True)
                r.render()

        if s.units == 'degrees':
            angles = [ u'0°', u'30°', u'60°', u'90°', u'120°', u'150°',
                       u'180°', u'210°', u'240°', u'270°', u'300°', u'330°' ]
        else:
            angles = [ '0', u'π/6', u'π/3', u'π/2', u'2π/3', u'5π/6',
                       u'π', u'7π/6', u'4π/3', u'3π/2', u'5π/3', u'11π/6' ]

        align = [ (-1, 1), (-1, 1), (-1, 1), (0, 1), (1, 1), (1, 1),
                  (1, 0), (1, -1), (1, -1), (0, -1), (-1, -1), (-1, -1) ]

        if s.direction == 'anticlockwise':
            angles = angles[0:1] + angles[1:][::-1]
        
        # rotate labels if zero not at right
        if s.position0 == 'top':
            angles = angles[3:] + angles[:4]
        elif s.position0 == 'left':
            angles = angles[6:] + angles[:7]
        elif s.position0 == 'bottom':
            angles = angles[9:] + angles[:10]

        # draw labels around plot
        if not s.TickLabels.hidetangential:
            for i in xrange(12):
                angle = 2 * N.pi / 12
                x = self._xc +  N.cos(angle*i) * self._xscale
                y = self._yc +  N.sin(angle*i) * self._yscale
                r = utils.Renderer(painter, font, x, y, angles[i],
                                   alignhorz=align[i][0],
                                   alignvert=align[i][1],
                                   usefullheight=True)
                r.render()
            
        # draw spokes
        if not t.hidespokes:
            painter.setPen( s.Tick.makeQPenWHide(painter) )
            painter.setBrush( qt4.QBrush() )      
            angle = 2 * N.pi / 12
            lines = []
            for i in xrange(12):
                x = self._xc +  N.cos(angle*i) * self._xscale
                y = self._yc +  N.sin(angle*i) * self._yscale
                lines.append( qt4.QLineF(qt4.QPointF(self._xc, self._yc),
                                         qt4.QPointF(x, y)) )
            painter.drawLines(lines)

document.thefactory.register(Polar)
