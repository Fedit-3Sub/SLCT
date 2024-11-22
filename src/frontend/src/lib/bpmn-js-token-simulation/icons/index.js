import LogSVG from './log.svg?raw';
import AngleRightSVG from './angle-right.svg?raw';
import CheckCircleSVG from './check-circle.svg?raw';
import ForkSVG from './fork.svg?raw';
import ExclamationTriangleSVG from './exclamation-triangle.svg?raw';
import InfoSVG from './info.svg?raw';
import PauseSVG from './pause.svg?raw';
import RemovePauseSVG from './pause-remove.svg?raw';
import PlaySVG from './play.svg?raw';
import ResetSVG from './reset.svg?raw';
import TachometerSVG from './tachometer-alt.svg?raw';
import TimesCircleSVG from './times-circle.svg?raw';
import TimesSVG from './times.svg?raw';
import ToggleOffSVG from './toggle-off.svg?raw';
import ToggleOnSVG from './toggle-on.svg?raw';


function createIcon(svg) {
  return function Icon(className = '') {
    return `<span class="bts-icon ${ className }">${svg}</span>`;
  };
}

export const LogIcon = createIcon(LogSVG);
export const AngleRightIcon = createIcon(AngleRightSVG);
export const CheckCircleIcon = createIcon(CheckCircleSVG);
export const RemovePauseIcon = createIcon(RemovePauseSVG);
export const ForkIcon = createIcon(ForkSVG);
export const ExclamationTriangleIcon = createIcon(ExclamationTriangleSVG);
export const InfoIcon = createIcon(InfoSVG);
export const PauseIcon = createIcon(PauseSVG);
export const PlayIcon = createIcon(PlaySVG);
export const ResetIcon = createIcon(ResetSVG);
export const TachometerIcon = createIcon(TachometerSVG);
export const TimesCircleIcon = createIcon(TimesCircleSVG);
export const TimesIcon = createIcon(TimesSVG);
export const ToggleOffIcon = createIcon(ToggleOffSVG);
export const ToggleOnIcon = createIcon(ToggleOnSVG);
