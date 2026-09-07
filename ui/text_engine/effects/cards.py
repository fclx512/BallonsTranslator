"""Reusable cards and controls for item-wide text effects.

Port of upstream v1.5.13 ``cards.py`` with the fork scope trim (image /
texture / alpha-mask cards removed; FilterEffectCard re-added with the
filter pipeline) and the parameter area laid out to the
``TransformParameterPanel`` spec: right-aligned labels, 22px editors,
two-column grid with span-2 rows for fill, blend, and the gradient
editor (2026-09-03 user decision, kept for the re-port).
Fork further retires the standalone stroke card (2026-09-08: duplicate
of the main panel stroke row, which writes the same stack entry via the
legacy views) and swaps QColorDialog for the fork's own
``ui/custom_widget/color_picker.py::ColorPickerDialog`` everywhere.
"""

from typing import Dict, Optional, Sequence, Tuple

from qtpy.QtCore import (
    QCoreApplication,
    QEvent,
    QRectF,
    QSignalBlocker,
    Signal,
    QSize,
    Qt,
)
from qtpy.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QIcon,
    QMouseEvent,
    QPaintEvent,
    QPainter,
)
from qtpy.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ui.custom_widget.color_picker import ColorPickerDialog

from utils.text_effects import (
    EffectPaint,
    FilterEffect,
    GeneratedEffectPaint,
    GlowEffect,
    LinearGradientPaint,
    SHADOW_BLUR_LIMIT,
    SHADOW_DISTANCE_LIMIT,
    SHADOW_SPREAD_LIMIT,
    ShadowEffect,
    SolidPaint,
    TextFillEffect,
)

from ui.custom_widget.combobox import BottomBorderComboBox
from ui.icon_rendering import render_svg_pixmap
from ui.misc import themed_icon_path
from ..transforms.panel import CommittedTransformControl, TransformDragLabel
from .gradient_editor import GradientAngleDial, InlineLinearGradientEditor
from .paint import paint_effect_paint_preview
from .filters import (
    FilterParamSpec,
    FilterSpec,
    FilterUnavailableError,
    get_filter_registry,
)


def _filter_ui_text(spec: FilterSpec, text: str) -> str:
    """Translate static built-in metadata in one extractable UI context."""
    if not spec.builtin:
        return text
    translations = {
        'Noise': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Noise'
        ),
        'Grain': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Grain'
        ),
        'Gaussian Blur': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Gaussian Blur'
        ),
        'Bloom': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Bloom'
        ),
        'Glitch': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Glitch'
        ),
        'Amount': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Amount'
        ),
        'Color': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Color'
        ),
        'Monochrome': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Monochrome'
        ),
        'Seed': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Seed'
        ),
        'Size': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Size'
        ),
        'Hardness': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Hardness'
        ),
        'Radius': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Radius'
        ),
        'Threshold': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Threshold'
        ),
        'Intensity': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Intensity'
        ),
        'Shift': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Shift'
        ),
        'Block Size': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Block Size'
        ),
        'Activity': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'Activity'
        ),
        'RGB Split': lambda: QCoreApplication.translate(
            'TextEffectPanel', 'RGB Split'
        ),
    }
    translator = translations.get(text)
    return text if translator is None else translator()


class _EffectActionButton(QToolButton):
    """Shared construction for compact effect-card actions."""

    def __init__(
        self,
        icon_name: str,
        hint: str,
        object_name: str,
        direction: int,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setIcon(QIcon(themed_icon_path(icon_name)))
        icon_extent = 12 if direction == 0 else 16
        self.setIconSize(QSize(icon_extent, icon_extent))
        self.setToolTip(hint)
        self.setAccessibleName(hint)
        self.setProperty('move-direction', direction)
        self.setFixedSize(18, 18)


class EffectDeleteButton(_EffectActionButton):
    """Delete an effect card."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            'titlebar_close.svg',
            QCoreApplication.translate('EffectDeleteButton', 'Delete'),
            'TextEffectCloseButton',
            0,
            parent,
        )


class EffectMoveUpButton(_EffectActionButton):
    """Move an effect toward the start of its stack."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            'chevron-up.svg',
            QCoreApplication.translate('EffectMoveUpButton', 'Move Up'),
            'TextEffectMoveButton',
            -1,
            parent,
        )


class EffectMoveDownButton(_EffectActionButton):
    """Move an effect toward the end of its stack."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            'chevron-down.svg',
            QCoreApplication.translate(
                'EffectMoveDownButton', 'Move Down'
            ),
            'TextEffectMoveButton',
            1,
            parent,
        )


class EffectVisibilityButton(QToolButton):
    """Compact enabled or disabled visibility control."""

    visibility_requested = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._visibility = True
        self.setObjectName('TextEffectVisibilityButton')
        self.setFixedSize(18, 18)
        self.setIconSize(QSize(16, 16))
        self.clicked.connect(self._on_clicked)
        self.set_visibility(True)

    def set_visibility(self, visible: bool) -> None:
        self._visibility = bool(visible)
        if self._visibility:
            icon_name = 'text-effect-visibility-open.svg'
            hint = self.tr('Hide')
        else:
            icon_name = 'text-effect-visibility-closed.svg'
            hint = self.tr('Show')
        self.setIcon(QIcon(themed_icon_path(icon_name)))
        self.setToolTip(hint)
        self.setAccessibleName(hint)

    def _on_clicked(self) -> None:
        self.visibility_requested.emit(not self._visibility)


class _EffectCard(QFrame):
    """Card base: hover-revealed action icons and matched-state styling."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._hovered = False
        self._matched = False
        self._keyboard_focused_action: Optional[QToolButton] = None
        self._hover_actions: Tuple[Tuple[QToolButton, object], ...] = ()
        self.setProperty('matched', False)

    def set_matched(self, matched: bool) -> None:
        matched = bool(matched)
        if self._matched == matched:
            return
        self._matched = matched
        self.setProperty('matched', matched)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_hover_actions(
        self, buttons: Sequence[QToolButton]
    ) -> None:
        self._hover_actions = tuple(
            (button, button.icon()) for button in buttons
        )
        for button, _icon in self._hover_actions:
            button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            button.installEventFilter(self)
        self._sync_action_icons()

    def _sync_action_icons(self) -> None:
        visible = self._hovered or self._keyboard_focused_action is not None
        for button, icon in self._hover_actions:
            button.setIcon(icon if visible else QIcon())

    def eventFilter(self, watched: QWidget, event: QEvent) -> bool:
        if any(watched is button for button, _icon in self._hover_actions):
            if event.type() == QEvent.Type.FocusIn:
                keyboard_reasons = {
                    Qt.FocusReason.TabFocusReason,
                    Qt.FocusReason.BacktabFocusReason,
                    Qt.FocusReason.ShortcutFocusReason,
                }
                self._keyboard_focused_action = (
                    watched if event.reason() in keyboard_reasons else None
                )
                self._sync_action_icons()
            elif (
                event.type() == QEvent.Type.FocusOut
                and watched is self._keyboard_focused_action
            ):
                self._keyboard_focused_action = None
                self._sync_action_icons()
        return super().eventFilter(watched, event)

    def enterEvent(self, event: QEvent) -> None:
        self._hovered = True
        self._sync_action_icons()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._hovered = False
        self._sync_action_icons()
        super().leaveEvent(event)


def _effect_icon_label(
    icon_name: str,
    parent: QWidget,
) -> QLabel:
    label = QLabel(parent)
    label.setObjectName('TextEffectParameterIcon')
    label.setFixedSize(16, 16)
    label.setPixmap(render_svg_pixmap(
        themed_icon_path(icon_name),
        16,
        16,
        parent.devicePixelRatioF(),
    ))
    return label


def _effect_action_widget(
    parent: _EffectCard,
    buttons: Sequence[QToolButton],
) -> QWidget:
    widget = QWidget(parent)
    widget.setObjectName('TextEffectPanelActions')
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    for button in buttons:
        layout.addWidget(button)
    widget.setFixedWidth(18 * len(buttons) + 4 * max(0, len(buttons) - 1))
    parent.set_hover_actions(buttons)
    return widget


def _set_effect_selector_width(
    selector: BottomBorderComboBox,
) -> None:
    """Let effect selectors share their grid column and shrink to the dock.

    The old ``setWidthSampleText('Long / Extrude')`` raised the selector's
    minimum width to ~198px.  The fork right panel is only 348px wide, so a
    Shadow card (whose two-column grid then needed ~382px) clipped the span-2
    blend/Fill rows.  Shrinkable selectors let Qt compress the card to the
    available width instead (the sizeHint is ignored, 150px ceiling keeps a
    single selector from blowing out its column).  Cards are still sized by
    their content when the panel is wide.

    The 72px floor keeps an Ignored-policy selector sharing a row with a
    stretch-1 sibling (the Fill row's paint swatch) from being squeezed to
    zero width — it silently vanished there under the 348px panel
    (2026-09-08 实机验收缺陷).
    """
    selector.setSizePolicy(
        QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
    )
    selector.setMinimumWidth(72)
    selector.setMaximumWidth(150)


class BlendModeSelector(QToolButton):
    """Compact selector with native blend-family submenus."""

    mode_changed = Signal(str)
    ARROW_SIZE = 12

    def __init__(
        self,
        accessible_context: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._accessible_context = accessible_context
        self._current_mode = 'normal'
        self._actions_by_mode: Dict[str, QAction] = {}
        self.setObjectName('TextEffectBlendSelector')
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )

        menu = QMenu(self)
        menu.setObjectName('TextEffectBlendMenu')
        self._action_group = QActionGroup(self)
        self._action_group.setExclusive(True)
        self._add_action(
            menu,
            QCoreApplication.translate('TextEffectPanel', 'Normal'),
            'normal',
        )
        darken_menu = menu.addMenu(
            QCoreApplication.translate('TextEffectPanel', 'Darken')
        )
        darken_menu.setObjectName('TextEffectBlendMenu')
        for label, mode in (
            (QCoreApplication.translate('TextEffectPanel', 'Darken'), 'darken'),
            (
                QCoreApplication.translate('TextEffectPanel', 'Multiply'),
                'multiply',
            ),
            (
                QCoreApplication.translate('TextEffectPanel', 'Color Burn'),
                'color_burn',
            ),
            (
                QCoreApplication.translate('TextEffectPanel', 'Linear Burn'),
                'linear_burn',
            ),
            (
                QCoreApplication.translate('TextEffectPanel', 'Darker Color'),
                'darker_color',
            ),
        ):
            self._add_action(darken_menu, label, mode)

        lighten_menu = menu.addMenu(
            QCoreApplication.translate('TextEffectPanel', 'Lighten')
        )
        lighten_menu.setObjectName('TextEffectBlendMenu')
        for label, mode in (
            (
                QCoreApplication.translate('TextEffectPanel', 'Lighten'),
                'lighten',
            ),
            (
                QCoreApplication.translate('TextEffectPanel', 'Screen'),
                'screen',
            ),
            (
                QCoreApplication.translate('TextEffectPanel', 'Color Dodge'),
                'color_dodge',
            ),
            (
                QCoreApplication.translate(
                    'TextEffectPanel', 'Linear Dodge (Add)'
                ),
                'linear_dodge',
            ),
            (
                QCoreApplication.translate('TextEffectPanel', 'Lighter Color'),
                'lighter_color',
            ),
        ):
            self._add_action(lighten_menu, label, mode)
        self._action_group.triggered.connect(self._on_action_triggered)
        self.setMenu(menu)
        self.set_mode('normal')

    def _add_action(self, menu: QMenu, label: str, mode: str) -> None:
        action = menu.addAction(label)
        action.setCheckable(True)
        action.setData(mode)
        self._action_group.addAction(action)
        self._actions_by_mode[mode] = action

    def current_mode(self) -> str:
        return self._current_mode

    def set_mode(self, mode: str) -> None:
        action = self._actions_by_mode.get(mode)
        if action is None:
            raise ValueError('unsupported blend mode')
        self._current_mode = mode
        for candidate in self._action_group.actions():
            candidate.setChecked(candidate is action)
        label = action.text()
        self.setText(label)
        self.setAccessibleName(f'{self._accessible_context}: {label}')

    def _on_action_triggered(self, action: QAction) -> None:
        mode = str(action.data())
        if mode == self._current_mode or mode not in self._actions_by_mode:
            return
        self.set_mode(mode)
        self.mode_changed.emit(mode)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        pixmap = render_svg_pixmap(
            themed_icon_path('chevron-down.svg'),
            self.ARROW_SIZE,
            self.ARROW_SIZE,
            self.devicePixelRatioF(),
        )
        x = self.width() - self.ARROW_SIZE - 4
        y = (self.height() - self.ARROW_SIZE) // 2
        painter.drawPixmap(x, y, pixmap)
        painter.end()


def _labeled_effect_editor(
    parent: QWidget, label_text: str, editor: QWidget
) -> QWidget:
    """Build the shared compact label/editor row used by effect cards."""
    label = QLabel(label_text, parent)
    label.setObjectName('TextEffectParamLabel')
    label.setAlignment(
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    )
    widget = QWidget(parent)
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.addWidget(label)
    layout.addWidget(editor, 1)
    return widget


def _blend_control(
    parent: QWidget,
    accessible_name: str,
) -> Tuple[QWidget, BlendModeSelector]:
    """Build the shared blend-mode row."""
    selector = BlendModeSelector(accessible_name, parent)
    tooltip = QCoreApplication.translate(
        'TextEffectPanel',
        'Blends with earlier output in the text-effect stack, not the page '
        'image or backdrop.',
    )
    selector.setToolTip(tooltip)
    selector.setAccessibleDescription(tooltip)
    return _labeled_effect_editor(
        parent,
        QCoreApplication.translate('TextEffectPanel', 'Blend'),
        selector,
    ), selector


def _set_blend_value(
    selector: BlendModeSelector,
    effect: object,
) -> None:
    selector.set_mode(getattr(effect, 'blend_mode'))


class EffectNumericControl(CommittedTransformControl):
    """Reuse the committed numeric editor with typed-text preview signals."""

    value_preview_requested = Signal(str, object)
    value_preview_canceled = Signal(str)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setObjectName('TextEffectControl')
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.label.setObjectName('TextEffectParamLabel')
        self.label.setWordWrap(False)
        self.label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.editor.setObjectName('TextEffectParamEditor')
        self.editor.setProperty('cardEditor', True)
        self.editor.setMinimumWidth(0)
        self.editor.setMaximumWidth(16777215)
        self.editor.setFixedHeight(22)
        self.editor.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.layout().setSpacing(8)
        self.layout().setStretch(0, 0)
        self.layout().setStretch(1, 1)

    def _on_text_edited(self) -> None:
        super()._on_text_edited()
        try:
            value = self._parse(self.editor.text())
        except (TypeError, ValueError):
            return
        self.value_preview_requested.emit(self.param_name, value)

    @property
    def model_value(self) -> Optional[float]:
        return self._model_value

    def show_preview_value(self, value: float) -> None:
        self.editor.setText(self._format(value))

    def restore_model_display(self) -> None:
        self._restore_display()

    def commit_pending(self) -> bool:
        was_pending = self.state == self.PENDING_TEXT
        committed = super().commit_pending()
        if was_pending and not committed:
            self.value_preview_canceled.emit(self.param_name)
        return committed

    def cancel_pending(self) -> None:
        was_pending = self.state == self.PENDING_TEXT
        super().cancel_pending()
        if was_pending:
            self.value_preview_canceled.emit(self.param_name)


class EffectPaintButton(QToolButton):
    """Compact solid swatch or rendered linear-gradient strip."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._paint: Optional[GeneratedEffectPaint] = None
        self.setObjectName('TextEffectPaintButton')
        self.setMinimumHeight(24)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

    def set_paint(
        self,
        paint: GeneratedEffectPaint,
        description: Optional[str] = None,
    ) -> None:
        self._paint = paint
        self.setIcon(QIcon())
        self.setText('')
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        if description is None:
            description = (
                self.tr('Edit Gradient')
                if isinstance(paint, LinearGradientPaint)
                else self.tr('Choose Color')
            )
        self.setToolTip(description)
        self.setAccessibleName(description)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if self._paint is None:
            return
        rect = QRectF(self.contentsRect()).adjusted(4.0, 3.0, -4.0, -3.0)
        if rect.width() <= 0.0 or rect.height() <= 0.0:
            return
        painter = QPainter(self)
        paint_effect_paint_preview(
            painter,
            rect,
            self._paint,
            self.palette(),
            self.devicePixelRatioF(),
        )


class _EffectCardMixin:
    """Shared signal re-emitters for the four typed effect cards."""

    def _on_enabled_clicked(self, enabled: bool) -> None:
        self.value_commit_requested.emit(
            self.index, 'enabled', bool(enabled)
        )

    def _on_control_commit(self, name: str, value) -> None:
        self.value_commit_requested.emit(self.index, name, value)

    def _on_value_preview(self, name: str, value) -> None:
        self.value_preview_requested.emit(self.index, name, value)

    def _on_parameter_preview(self, name: str, delta) -> None:
        self.parameter_preview_requested.emit(self.index, name, delta)

    def _on_parameter_commit(self, name: str, delta) -> None:
        self.parameter_commit_requested.emit(self.index, name, delta)

    def _on_preview_canceled(self, name: str) -> None:
        self.preview_canceled.emit(self.index, name)

    def _on_action_clicked(self) -> None:
        button = self.sender()
        direction = int(button.property('move-direction'))
        if direction == 0:
            self.remove_requested.emit(self.index)
        else:
            self.move_requested.emit(self.index, direction)

    def _on_gradient_preview(self, paint: LinearGradientPaint) -> None:
        self.value_preview_requested.emit(self.index, 'paint', paint)

    def _on_gradient_commit(self, paint: LinearGradientPaint) -> None:
        self.value_commit_requested.emit(self.index, 'paint', paint)

    def _on_gradient_cancel(self) -> None:
        self.preview_canceled.emit(self.index, 'paint')

    def _connect_gradient_editor(self, editor) -> None:
        editor.paint_previewed.connect(self._on_gradient_preview)
        editor.paint_commit_requested.connect(self._on_gradient_commit)
        editor.paint_preview_canceled.connect(self._on_gradient_cancel)
        editor.color_dialog_active_changed.connect(
            self.color_dialog_active_changed.emit
        )
        editor.hide()

    def _build_paint_row(
        self,
        accessible_fill_name: str,
    ) -> QWidget:
        """Build the span-2 fill row: Fill type selector + paint swatch.

        本方法在 mixin 里，``self.tr`` 运行时上下文是各卡片类名，而
        i18n 提取器按物理位置归到 _EffectCardMixin——两边对不上，
        词条永不命中（2026-09-08 实机：Fill 行英文漏翻）。按项目惯例
        在字面量定义处显式标注 TextEffectPanel 上下文。
        """
        fill_label = QLabel(
            QCoreApplication.translate('TextEffectPanel', 'Fill'), self
        )
        fill_label.setObjectName('TextEffectParamLabel')
        fill_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.fill_type_selector = BottomBorderComboBox(
            self, text_alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.fill_type_selector.setObjectName('TextEffectParamEditor')
        self.fill_type_selector.setAccessibleName(accessible_fill_name)
        _set_effect_selector_width(self.fill_type_selector)
        self.fill_type_selector.addItem(
            QCoreApplication.translate('TextEffectPanel', 'Solid'), 'solid'
        )
        self.fill_type_selector.addItem(
            QCoreApplication.translate('TextEffectPanel', 'Gradient'),
            'linear_gradient',
        )
        self.fill_type_selector.currentIndexChanged.connect(
            self._on_fill_type_changed
        )
        self.paint_button = EffectPaintButton(self)
        self.paint_button.clicked.connect(self._on_paint_clicked)
        self._paint_seed: Optional[GeneratedEffectPaint] = None

        row = QWidget(self)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        row_layout.addWidget(fill_label)
        row_layout.addWidget(self.fill_type_selector)
        row_layout.addWidget(self.paint_button, 1)
        return row

    def _sync_paint_value(self, paint: GeneratedEffectPaint) -> None:
        """Echo paint type + seed; toggle gradient editor visibility."""
        with QSignalBlocker(self.fill_type_selector):
            self.fill_type_selector.setCurrentIndex(
                self.fill_type_selector.findData(paint.paint_type)
            )
        self._paint_seed = paint
        show_gradient = paint.paint_type == 'linear_gradient'
        visibility_changed = (
            self.gradient_editor.isHidden() == show_gradient
        )
        self.paint_button.setVisible(not show_gradient)
        self.gradient_editor.setVisible(show_gradient)
        if show_gradient and isinstance(paint, LinearGradientPaint):
            self.gradient_editor.set_paint(paint)
        if visibility_changed:
            self._controls_layout.invalidate()
            self.layout().invalidate()
            self.updateGeometry()

    def _on_fill_type_changed(self, combo_index: int) -> None:
        if combo_index >= 0:
            self.value_commit_requested.emit(
                self.index,
                'paint_type',
                self.fill_type_selector.itemData(combo_index),
            )

    def _on_blend_changed(self, blend_mode: str) -> None:
        self.value_commit_requested.emit(
            self.index, 'blend_mode', blend_mode
        )

    def _on_paint_clicked(self) -> None:
        paint = self._paint_seed
        if not isinstance(paint, SolidPaint):
            return
        self.color_dialog_active_changed.emit(True)
        try:
            dialog = ColorPickerDialog(QColor(*paint.color), self.window())
            accepted = dialog.exec_() == QDialog.DialogCode.Accepted
            color = dialog.get_color()
            if accepted and color.isValid():
                self.value_commit_requested.emit(
                    self.index,
                    'paint',
                    SolidPaint((color.red(), color.green(), color.blue())),
                )
        finally:
            self.color_dialog_active_changed.emit(False)

    def _build_header(
        self,
        icon_name: str,
        title: str,
    ) -> QHBoxLayout:
        self.move_up_button = EffectMoveUpButton(self)
        self.move_down_button = EffectMoveDownButton(self)
        self.delete_button = EffectDeleteButton(self)
        for button in (
            self.move_up_button,
            self.move_down_button,
            self.delete_button,
        ):
            button.clicked.connect(self._on_action_clicked)
        self.visibility_button = EffectVisibilityButton(self)
        self.visibility_button.visibility_requested.connect(
            self._on_enabled_clicked
        )
        action_widget = _effect_action_widget(
            self,
            (
                self.move_up_button,
                self.move_down_button,
                self.delete_button,
            ),
        )
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)
        self.title_icon_label = _effect_icon_label(icon_name, self)
        self.title_label = QLabel(title, self)
        self.title_label.setObjectName('TextEffectParameterTitle')
        header.addWidget(self.title_icon_label)
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(action_widget)
        header.addWidget(self.visibility_button)
        return header


class ShadowEffectCard(_EffectCard, _EffectCardMixin):
    """Edit one typed Shadow at its complete-stack index."""

    value_commit_requested = Signal(int, str, object)
    value_preview_requested = Signal(int, str, object)
    parameter_preview_requested = Signal(int, str, object)
    parameter_commit_requested = Signal(int, str, object)
    preview_canceled = Signal(int, str)
    remove_requested = Signal(int)
    move_requested = Signal(int, int)
    color_dialog_active_changed = Signal(bool)

    def __init__(self, index: int, parent=None) -> None:
        super().__init__(parent)
        self.index = int(index)
        self.setObjectName('TextEffectParameterPanel')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        header = self._build_header('text-effect-shadow.svg', self.tr('Shadow'))

        self.type_selector = BottomBorderComboBox(
            self, text_alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.type_selector.setObjectName('TextEffectParamEditor')
        self.type_selector.setAccessibleName(self.tr('Shadow Type'))
        for label, value in (
            (self.tr('Drop'), 'drop'),
            (self.tr('Inner'), 'inner'),
            (self.tr('Long / Extrude'), 'long'),
        ):
            self.type_selector.addItem(label, value)
        _set_effect_selector_width(self.type_selector)
        self.type_selector.currentIndexChanged.connect(
            self._on_type_changed
        )

        self.opacity_control = EffectNumericControl(
            self.tr('Opacity'), 'opacity', 100.0, 0.0, 1.0, '%', 1.0,
            self, decimals=1,
        )
        self.angle_control = EffectNumericControl(
            self.tr('Angle'), 'angle', 1.0, 0.0, 359.9, '°', 1.0,
            self, decimals=1,
        )
        self.angle_dial = GradientAngleDial(self)
        self.angle_dial.setToolTip(self.tr('Drag to set shadow angle'))
        self.angle_dial.setAccessibleName(self.tr('Shadow Angle'))
        angle_layout = self.angle_control.layout()
        angle_layout.insertWidget(1, self.angle_dial)
        self.angle_dial.angle_previewed.connect(
            self._on_angle_dial_preview
        )
        self.angle_dial.angle_commit_requested.connect(
            self._on_angle_dial_commit
        )
        self.angle_dial.angle_preview_canceled.connect(
            self._on_angle_dial_cancel
        )
        self.distance_control = EffectNumericControl(
            self.tr('Distance'), 'distance', 1.0,
            0.0, SHADOW_DISTANCE_LIMIT, '', 0.01,
            self, decimals=2,
        )
        self.blur_control = EffectNumericControl(
            self.tr('Blur'), 'blur', 1.0, 0.0,
            SHADOW_BLUR_LIMIT, '', 0.01,
            self, decimals=2,
        )
        self.spread_control = EffectNumericControl(
            self.tr('Spread'), 'spread', 1.0, 0.0,
            SHADOW_SPREAD_LIMIT, '', 0.01,
            self, decimals=2,
        )
        blend_widget, self.blend_selector = _blend_control(
            self, self.tr('Shadow Blend')
        )
        self.blend_selector.mode_changed.connect(
            self._on_blend_changed
        )
        for control in self.iter_controls():
            control.commit_requested.connect(self._on_control_commit)
            control.value_preview_requested.connect(self._on_value_preview)
            control.preview_requested.connect(self._on_parameter_preview)
            control.drag_commit_requested.connect(
                self._on_parameter_commit
            )
            control.preview_canceled.connect(self._on_preview_canceled)
            control.value_preview_canceled.connect(
                self._on_preview_canceled
            )

        self.gradient_editor = InlineLinearGradientEditor(
            LinearGradientPaint(), self
        )
        self._connect_gradient_editor(self.gradient_editor)

        paint_row = self._build_paint_row(self.tr('Shadow Fill'))

        controls = QGridLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setHorizontalSpacing(8)
        controls.setVerticalSpacing(8)
        controls.addWidget(self.type_selector, 0, 0)
        controls.addWidget(self.opacity_control, 0, 1)
        controls.addWidget(self.angle_control, 1, 0)
        controls.addWidget(self.distance_control, 1, 1)
        controls.addWidget(self.blur_control, 2, 0)
        controls.addWidget(self.spread_control, 2, 1)
        controls.addWidget(paint_row, 3, 0, 1, 2)
        controls.addWidget(blend_widget, 4, 0, 1, 2)
        controls.addWidget(self.gradient_editor, 5, 0, 1, 2)
        controls.setColumnStretch(0, 1)
        controls.setColumnStretch(1, 1)
        self._controls_layout = controls

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(8)
        layout.addLayout(header)
        layout.addLayout(controls)

    def set_move_enabled(self, up: bool, down: bool) -> None:
        self.move_up_button.setEnabled(up)
        self.move_down_button.setEnabled(down)

    def set_value(self, shadow: ShadowEffect) -> None:
        self.visibility_button.set_visibility(shadow.enabled)
        _set_blend_value(self.blend_selector, shadow)
        with QSignalBlocker(self.type_selector):
            self.type_selector.setCurrentIndex(
                self.type_selector.findData(shadow.shadow_type)
            )
        show_soft_controls = shadow.shadow_type != 'long'
        self.blur_control.setVisible(show_soft_controls)
        self.spread_control.setVisible(show_soft_controls)
        if shadow.shadow_type == 'inner':
            self.spread_control.label.setText(self.tr('Choke'))
        else:
            self.spread_control.label.setText(self.tr('Spread'))

        for name, control in (
            ('opacity', self.opacity_control),
            ('angle', self.angle_control),
            ('distance', self.distance_control),
            ('blur', self.blur_control),
            ('spread', self.spread_control),
        ):
            control.set_model_value(getattr(shadow, name))
        self.angle_dial.end_interaction()
        self.angle_dial.set_angle(shadow.angle)
        self._sync_paint_value(shadow.paint)
        self.paint_button.set_paint(
            self._paint_seed,
            description=(
                self.tr('Edit Shadow Gradient')
                if isinstance(shadow.paint, LinearGradientPaint)
                else self.tr('Choose Shadow Color')
            ),
        )

    def iter_controls(self) -> Tuple[EffectNumericControl, ...]:
        return (
            self.opacity_control,
            self.angle_control,
            self.distance_control,
            self.blur_control,
            self.spread_control,
        )

    def _on_type_changed(self, combo_index: int) -> None:
        if combo_index >= 0:
            self.value_commit_requested.emit(
                self.index,
                'shadow_type',
                self.type_selector.itemData(combo_index),
            )

    def _on_control_commit(self, name: str, value) -> None:
        if name == 'angle':
            self.angle_dial.set_angle(value)
        self.value_commit_requested.emit(self.index, name, value)

    def _on_value_preview(self, name: str, value) -> None:
        if name == 'angle':
            self.angle_dial.set_angle(value)
        self.value_preview_requested.emit(self.index, name, value)

    def _on_parameter_preview(self, name: str, delta) -> None:
        if name == 'angle' and self.angle_control.model_value is not None:
            self.angle_dial.set_angle(
                self.angle_control.model_value + delta
            )
        self.parameter_preview_requested.emit(self.index, name, delta)

    def _on_parameter_commit(self, name: str, delta) -> None:
        if name == 'angle' and self.angle_control.model_value is not None:
            self.angle_dial.set_angle(
                self.angle_control.model_value + delta
            )
        self.parameter_commit_requested.emit(self.index, name, delta)

    def _on_preview_canceled(self, name: str) -> None:
        if name == 'angle' and self.angle_control.model_value is not None:
            self.angle_dial.set_angle(self.angle_control.model_value)
        self.preview_canceled.emit(self.index, name)

    def _on_angle_dial_preview(self, angle: float) -> None:
        self.angle_control.show_preview_value(angle)
        self.value_preview_requested.emit(self.index, 'angle', angle)

    def _on_angle_dial_commit(self) -> None:
        angle = self.angle_dial.angle
        self.angle_control.set_model_value(angle, (angle,))
        self.value_commit_requested.emit(self.index, 'angle', angle)

    def _on_angle_dial_cancel(self) -> None:
        self.angle_control.restore_model_display()
        self.preview_canceled.emit(self.index, 'angle')


class GlowEffectCard(_EffectCard, _EffectCardMixin):
    """Edit one typed Glow at its complete-stack index."""

    value_commit_requested = Signal(int, str, object)
    value_preview_requested = Signal(int, str, object)
    parameter_preview_requested = Signal(int, str, object)
    parameter_commit_requested = Signal(int, str, object)
    preview_canceled = Signal(int, str)
    remove_requested = Signal(int)
    move_requested = Signal(int, int)
    color_dialog_active_changed = Signal(bool)

    def __init__(self, index: int, parent=None) -> None:
        super().__init__(parent)
        self.index = int(index)
        self.setObjectName('TextEffectParameterPanel')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        header = self._build_header('text-effect-glow.svg', self.tr('Glow'))

        self.type_selector = BottomBorderComboBox(
            self, text_alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.type_selector.setObjectName('TextEffectParamEditor')
        self.type_selector.setAccessibleName(self.tr('Glow Type'))
        self.type_selector.addItem(self.tr('Outer'), 'outer')
        self.type_selector.addItem(self.tr('Inner'), 'inner')
        _set_effect_selector_width(self.type_selector)
        self.type_selector.currentIndexChanged.connect(
            self._on_type_changed
        )

        self.opacity_control = EffectNumericControl(
            self.tr('Opacity'), 'opacity', 100.0, 0.0, 1.0, '%', 1.0,
            self, decimals=1,
        )
        self.size_control = EffectNumericControl(
            self.tr('Size'), 'size', 1.0, 0.0,
            SHADOW_BLUR_LIMIT, '', 0.01, self, decimals=2,
        )
        self.spread_control = EffectNumericControl(
            self.tr('Spread'), 'spread', 1.0, 0.0,
            SHADOW_SPREAD_LIMIT, '', 0.01, self, decimals=2,
        )
        blend_widget, self.blend_selector = _blend_control(
            self, self.tr('Glow Blend')
        )
        self.blend_selector.mode_changed.connect(
            self._on_blend_changed
        )
        for control in self.iter_controls():
            control.commit_requested.connect(self._on_control_commit)
            control.value_preview_requested.connect(self._on_value_preview)
            control.preview_requested.connect(self._on_parameter_preview)
            control.drag_commit_requested.connect(
                self._on_parameter_commit
            )
            control.preview_canceled.connect(self._on_preview_canceled)
            control.value_preview_canceled.connect(
                self._on_preview_canceled
            )

        self.gradient_editor = InlineLinearGradientEditor(
            LinearGradientPaint(), self
        )
        self._connect_gradient_editor(self.gradient_editor)

        paint_row = self._build_paint_row(self.tr('Glow Fill'))

        controls = QGridLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setHorizontalSpacing(8)
        controls.setVerticalSpacing(8)
        controls.addWidget(self.type_selector, 0, 0)
        controls.addWidget(self.opacity_control, 0, 1)
        controls.addWidget(self.size_control, 1, 0)
        controls.addWidget(self.spread_control, 1, 1)
        controls.addWidget(paint_row, 2, 0, 1, 2)
        controls.addWidget(blend_widget, 3, 0, 1, 2)
        controls.addWidget(self.gradient_editor, 4, 0, 1, 2)
        controls.setColumnStretch(0, 1)
        controls.setColumnStretch(1, 1)
        self._controls_layout = controls

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(8)
        layout.addLayout(header)
        layout.addLayout(controls)

    def set_move_enabled(self, up: bool, down: bool) -> None:
        self.move_up_button.setEnabled(up)
        self.move_down_button.setEnabled(down)

    def set_value(self, glow: GlowEffect) -> None:
        self.visibility_button.set_visibility(glow.enabled)
        _set_blend_value(self.blend_selector, glow)
        with QSignalBlocker(self.type_selector):
            self.type_selector.setCurrentIndex(
                self.type_selector.findData(glow.glow_type)
            )
        if glow.glow_type == 'inner':
            self.spread_control.label.setText(self.tr('Choke'))
        else:
            self.spread_control.label.setText(self.tr('Spread'))

        for name, control in (
            ('opacity', self.opacity_control),
            ('size', self.size_control),
            ('spread', self.spread_control),
        ):
            control.set_model_value(getattr(glow, name))
        self._sync_paint_value(glow.paint)
        self.paint_button.set_paint(
            self._paint_seed,
            description=(
                self.tr('Edit Glow Gradient')
                if isinstance(glow.paint, LinearGradientPaint)
                else self.tr('Choose Glow Color')
            ),
        )

    def iter_controls(self) -> Tuple[EffectNumericControl, ...]:
        return (
            self.opacity_control,
            self.size_control,
            self.spread_control,
        )

    def _on_type_changed(self, combo_index: int) -> None:
        if combo_index >= 0:
            self.value_commit_requested.emit(
                self.index,
                'glow_type',
                self.type_selector.itemData(combo_index),
            )


class TextFillEffectCard(_EffectCard, _EffectCardMixin):
    """Edit one fixed Gradient foreground layer (texture is out of scope)."""

    value_commit_requested = Signal(int, str, object)
    value_preview_requested = Signal(int, str, object)
    parameter_preview_requested = Signal(int, str, object)
    parameter_commit_requested = Signal(int, str, object)
    preview_canceled = Signal(int, str)
    remove_requested = Signal(int)
    move_requested = Signal(int, int)
    color_dialog_active_changed = Signal(bool)

    def __init__(
        self,
        index: int,
        paint_type: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.index = int(index)
        if paint_type != 'linear_gradient':
            raise ValueError('unsupported foreground paint card type')
        self.paint_type = paint_type
        self.setObjectName('TextEffectParameterPanel')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        header = self._build_header(
            'text-effect-gradient.svg', self.tr('Gradient')
        )

        self.gradient_editor = InlineLinearGradientEditor(
            LinearGradientPaint(), self
        )
        self._connect_gradient_editor(self.gradient_editor)
        # 本卡即渐变卡：渐变编辑器（停点条+停点色块+角度/缩放）是它的
        # 主体交互，不像阴影/发光卡那样按 paint 类型切换显隐。此前沿用
        # _connect_gradient_editor 的初始 hide() 且无人再 show，编辑器
        # 永久隐藏、选色交互整个缺失（2026-09-08 实机验收缺陷）。
        self.gradient_editor.setVisible(True)

        self.opacity_control = EffectNumericControl(
            self.tr('Opacity'), 'opacity', 100.0, 0.0, 1.0, '%', 1.0,
            self, decimals=1,
        )
        for control in self.iter_controls():
            control.commit_requested.connect(self._on_control_commit)
            control.value_preview_requested.connect(self._on_value_preview)
            control.preview_requested.connect(self._on_parameter_preview)
            control.drag_commit_requested.connect(
                self._on_parameter_commit
            )
            control.preview_canceled.connect(self._on_preview_canceled)
            control.value_preview_canceled.connect(
                self._on_preview_canceled
            )
        blend_widget, self.blend_selector = _blend_control(
            self, self.tr('Gradient Blend')
        )
        self.blend_selector.mode_changed.connect(
            self._on_blend_changed
        )

        controls = QGridLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setHorizontalSpacing(8)
        controls.setVerticalSpacing(8)
        controls.setColumnStretch(0, 1)
        controls.setColumnStretch(1, 1)
        controls.addWidget(self.opacity_control, 0, 0)
        controls.addWidget(blend_widget, 0, 1)
        controls.addWidget(self.gradient_editor, 1, 0, 1, 2)
        self._controls_layout = controls

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(8)
        layout.addLayout(header)
        layout.addLayout(controls)

    def set_value(self, fill: TextFillEffect) -> None:
        """Project one foreground layer into this fixed card."""
        if fill.paint.paint_type != self.paint_type:
            raise ValueError(
                'foreground card values must match its paint type'
            )
        self.visibility_button.set_visibility(fill.enabled)
        _set_blend_value(self.blend_selector, fill)
        self.opacity_control.set_model_value(fill.opacity)
        self._paint_seed = fill.paint
        assert isinstance(self._paint_seed, LinearGradientPaint)
        self.gradient_editor.set_paint(self._paint_seed)
        self.layout().invalidate()
        self.updateGeometry()

    def iter_controls(self) -> Tuple[EffectNumericControl, ...]:
        return (self.opacity_control,)

    def set_move_enabled(self, up: bool, down: bool) -> None:
        self.move_up_button.setEnabled(up)
        self.move_down_button.setEnabled(down)


class FilterEffectCard(_EffectCard, _EffectCardMixin):
    """One repeatable lazy filter at its complete-stack index."""

    value_commit_requested = Signal(int, str, object)
    value_preview_requested = Signal(int, str, object)
    parameter_preview_requested = Signal(int, str, object)
    parameter_commit_requested = Signal(int, str, object)
    preview_canceled = Signal(int, str)
    remove_requested = Signal(int)
    move_requested = Signal(int, int)

    def __init__(
        self,
        index: int,
        filter_id: str,
        spec: Optional[FilterSpec],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.index = int(index)
        self.filter_id = filter_id
        self.spec = spec
        self.numeric_controls = {}
        self.choice_selectors = {}
        self.setObjectName('TextEffectParameterPanel')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        title = (
            _filter_ui_text(spec, spec.name)
            if spec is not None
            else self.tr('Missing Filter: {id}').format(id=filter_id)
        )
        header = self._build_header('text-effect-filter.svg', title)

        controls = QGridLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setHorizontalSpacing(8)
        controls.setVerticalSpacing(8)
        if spec is not None:
            for position, parameter in enumerate(spec.params):
                widget = self._parameter_widget(parameter)
                controls.addWidget(widget, position // 2, position % 2)
            controls.setColumnStretch(0, 1)
            controls.setColumnStretch(1, 1)
        self._controls_layout = controls

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(8)
        layout.addLayout(header)
        if spec is not None and spec.params:
            layout.addLayout(controls)

    def _parameter_widget(self, parameter: FilterParamSpec) -> QWidget:
        assert self.spec is not None
        signal_name = 'param:' + parameter.key
        label_text = _filter_ui_text(self.spec, parameter.label)
        if parameter.kind in {'float', 'int'}:
            assert parameter.minimum is not None
            assert parameter.maximum is not None
            control = EffectNumericControl(
                label_text,
                signal_name,
                parameter.display_factor,
                parameter.minimum,
                parameter.maximum,
                parameter.suffix,
                parameter.step,
                self,
                decimals=parameter.decimals,
            )
            control.commit_requested.connect(self._on_control_commit)
            control.value_preview_requested.connect(self._on_value_preview)
            control.preview_requested.connect(self._on_parameter_preview)
            control.drag_commit_requested.connect(self._on_parameter_commit)
            control.preview_canceled.connect(self._on_preview_canceled)
            control.value_preview_canceled.connect(self._on_preview_canceled)
            self.numeric_controls[parameter.key] = control
            return control

        selector = BottomBorderComboBox(
            self, text_alignment=Qt.AlignmentFlag.AlignCenter
        )
        selector.setObjectName('TextEffectParamEditor')
        selector.setProperty('filter-param', parameter.key)
        selector.setAccessibleName(label_text)
        _set_effect_selector_width(selector)
        choices = (
            (('Off', False), ('On', True))
            if parameter.kind == 'bool'
            else parameter.choices
        )
        for choice_label, value in choices:
            selector.addItem(
                _filter_ui_text(self.spec, choice_label), value
            )
        selector.currentIndexChanged.connect(self._on_choice_changed)
        self.choice_selectors[parameter.key] = selector
        return _labeled_effect_editor(self, label_text, selector)

    def set_move_enabled(self, up: bool, down: bool) -> None:
        self.move_up_button.setEnabled(up)
        self.move_down_button.setEnabled(down)

    def set_value(self, effect: FilterEffect) -> None:
        self.visibility_button.set_visibility(effect.enabled)
        if self.spec is None:
            return
        failure = get_filter_registry().get_runtime_failure(self.filter_id)
        if failure is not None:
            self._set_parameter_controls_enabled(False)
            self.setToolTip(str(failure))
            return
        try:
            if effect.schema_version == self.spec.schema_version:
                active_params = self.spec.normalize_params(
                    effect.params_dict()
                )
            elif (
                effect.enabled
                and effect.schema_version < self.spec.schema_version
            ):
                active_params = dict(
                    get_filter_registry().resolve(effect).params
                )
            else:
                raise FilterUnavailableError(
                    f'{self.spec.name} schema {effect.schema_version} '
                    'is incompatible; enable/update it to migrate.'
                )
        except (FilterUnavailableError, KeyError, ValueError) as error:
            self._set_parameter_controls_enabled(False)
            self.setToolTip(str(error))
            return
        self._set_parameter_controls_enabled(True)
        self.setToolTip('')
        for parameter in self.spec.params:
            value = active_params[parameter.key]
            control = self.numeric_controls.get(parameter.key)
            if control is not None:
                control.set_model_value(value)
                continue
            selector = self.choice_selectors[parameter.key]
            with QSignalBlocker(selector):
                selector.setCurrentIndex(selector.findData(value))

    def _set_parameter_controls_enabled(self, enabled: bool) -> None:
        for control in self.numeric_controls.values():
            control.setEnabled(enabled)
        for selector in self.choice_selectors.values():
            selector.setEnabled(enabled)

    def iter_controls(self) -> Tuple[EffectNumericControl, ...]:
        return tuple(self.numeric_controls.values())

    def _on_choice_changed(self, combo_index: int) -> None:
        selector = self.sender()
        if combo_index < 0 or not isinstance(selector, BottomBorderComboBox):
            return
        key = selector.property('filter-param')
        if isinstance(key, str) and key:
            self.value_commit_requested.emit(
                self.index, 'param:' + key, selector.itemData(combo_index)
            )
