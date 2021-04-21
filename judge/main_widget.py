import os

from PyQt5.QtCore import QTimer, QTime, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPixmap
from PyQt5.QtWidgets import QWidget, QTableWidget, QGridLayout, QTableWidgetItem, QMessageBox

COLUMNS_WIDTH = 120
COLOR_UNUSED = QColor(50, 48, 48)

FORMATIONS = ["Шеврон", "Окружность", "Треугольники", "Стрелка"]
PARTITIONS = ["Белая", "Красная", "Оранжевая", "Желтая", "Зеленая", "Голубая", "Синяя", "Серая"]


class MainWidget(QWidget):
    show_msg = pyqtSignal()

    def __init__(self, formation, prnt=None):
        super().__init__()

        self.formation = formation

        if prnt:
            self.prnt = prnt

        layout = QGridLayout()

        # noinspection PyUnresolvedReferences
        self.show_msg.connect(self.show_message)
        self.final_string = None

        self.table = QTableWidget()
        self.table.horizontalHeader().hide()
        self.table.verticalHeader().hide()

        self.table.setStyleSheet("QTableWidget { background-color: #808080; color: white; }")

        if formation:
            self.table.setColumnCount(4)
            self.table.setRowCount(6)
            self.table.setFixedWidth(COLUMNS_WIDTH * 4 + 2)
        else:
            self.table.setColumnCount(3)
            self.table.setRowCount(5)
            self.table.setFixedWidth(COLUMNS_WIDTH * 3 + 2)
        for i in range(self.table.colorCount()):
            self.table.setColumnWidth(i, COLUMNS_WIDTH)

        self.timer = QTimer()
        self.time = QTime(0, 0)
        self.timer.timeout.connect(self.timer_event)
        self.timer.start(1000)

        timer_item = QTableWidgetItem("00:00")
        timer_item.setData(Qt.FontRole, QFont("", 20))
        timer_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        timer_item.setFlags(Qt.NoItemFlags)
        self.table.setSpan(0, 0, 1, 4)
        self.table.setItem(0, 0, timer_item)

        fees_item = QTableWidgetItem("Штрафы")
        fees_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        fees_item.setFlags(Qt.NoItemFlags)
        self.table.setSpan(1, 0, 1, 4)
        self.table.setItem(1, 0, fees_item)

        coll_it = QTableWidgetItem("Столкновения")
        coll_it.setFlags(Qt.NoItemFlags)
        self.table.setItem(2, 0, coll_it)
        coll_it = QTableWidgetItem("0")
        coll_it.setFlags(Qt.NoItemFlags)
        self.table.setItem(2, 1, coll_it)

        if formation:
            out_it = QTableWidgetItem("Вылеты")
            out_it.setFlags(Qt.NoItemFlags)
            self.table.setItem(2, 2, out_it)
            out_it = QTableWidgetItem("0")
            out_it.setFlags(Qt.NoItemFlags)
            self.table.setItem(2, 3, out_it)
        else:
            unu_it = QTableWidgetItem()
            unu_it.setFlags(Qt.NoItemFlags)
            self.table.setItem(2, 2, unu_it)
            # self.table.item(2, 2).setBackground(COLOR_UNUSED)
            # unu_it = QTableWidgetItem()
            # unu_it.setFlags(Qt.NoItemFlags)
            # self.table.setItem(2, 3, unu_it)
            # self.table.item(2, 3).setBackground(COLOR_UNUSED)

        self.table.setSpan(3, 0, 1, 4)
        zones_it = QTableWidgetItem("Зоны")
        zones_it.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        zones_it.setFlags(Qt.NoItemFlags)
        self.table.setItem(3, 0, zones_it)

        if formation:
            self.table.setSpan(4, 0, 2, 1)
            self.table.setSpan(4, 1, 2, 1)
            self.table.setSpan(4, 2, 2, 1)
            self.table.setSpan(4, 3, 2, 1)
            n_it = QTableWidgetItem("Формация")
            n_it.setFlags(Qt.NoItemFlags)
            self.table.setItem(4, 0, n_it)
            sco_cur_it = QTableWidgetItem("СКО\nтекущее")
            sco_cur_it.setFlags(Qt.NoItemFlags)
            self.table.setItem(4, 1, sco_cur_it)
            sco_mean_it = QTableWidgetItem("СКО\nсреднее")
            sco_mean_it.setFlags(Qt.NoItemFlags)
            self.table.setItem(4, 2, sco_mean_it)
            t_it = QTableWidgetItem("Время\nперестроения")
            t_it.setFlags(Qt.NoItemFlags)
            self.table.setItem(4, 3, t_it)
        else:
            # self.table.setSpan(4, 1, 2, 1)
            # self.table.setSpan(4, 2, 2, 1)
            # self.table.setSpan(4, 3, 2, 1)
            n_it = QTableWidgetItem("Перегородка")
            n_it.setFlags(Qt.NoItemFlags)
            self.table.setItem(4, 0, n_it)
            t_it = QTableWidgetItem("Время")
            t_it.setFlags(Qt.NoItemFlags)
            self.table.setItem(4, 1, t_it)
            f_it = QTableWidgetItem("Штраф")
            f_it.setFlags(Qt.NoItemFlags)
            self.table.setItem(4, 2, f_it)
            # unu_it = QTableWidgetItem()
            # unu_it.setFlags(Qt.NoItemFlags)
            # self.table.setItem(4, 3, unu_it)
            # self.table.item(4, 3).setBackground(COLOR_UNUSED)

        layout.addWidget(self.table)

        self.setLayout(layout)
        self.add_row()

    def timer_event(self):
        self.time = self.time.addSecs(1)
        timer_item = QTableWidgetItem(self.time.toString("mm:ss"))
        timer_item.setData(Qt.FontRole, QFont("", 20))
        timer_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        timer_item.setFlags(Qt.NoItemFlags)
        self.table.setItem(0, 0, timer_item)

    def add_row(self):
        rc = self.table.rowCount()
        self.table.insertRow(rc)
        if self.formation:
            # noinspection PyBroadException
            try:
                it = QTableWidgetItem(str(FORMATIONS[rc - 6]))
                it.setFlags(Qt.NoItemFlags)
                self.table.setItem(rc, 0, it)
                unu_it = QTableWidgetItem()
                unu_it.setFlags(Qt.NoItemFlags)
                self.table.setItem(rc, 1, unu_it)
                unu_it = QTableWidgetItem()
                unu_it.setFlags(Qt.NoItemFlags)
                self.table.setItem(rc, 2, unu_it)
                unu_it = QTableWidgetItem()
                unu_it.setFlags(Qt.NoItemFlags)
                self.table.setItem(rc, 3, unu_it)

                img_pixmap = QPixmap(
                    "{}/imgs/formations/{}.png".format(os.path.dirname(__file__), rc - 5))
                self.prnt.img_label.setPixmap(
                    img_pixmap.scaled(self.prnt.img_label.width(), self.prnt.img_label.height()))
            except Exception:
                pass

        else:
            # noinspection PyBroadException
            try:
                it = QTableWidgetItem(str(PARTITIONS[rc - 5]))
                it.setFlags(Qt.NoItemFlags)
                self.table.setItem(rc, 0, it)
                unu_it = QTableWidgetItem()
                unu_it.setFlags(Qt.NoItemFlags)
                self.table.setItem(rc, 1, unu_it)
                unu_it = QTableWidgetItem()
                unu_it.setFlags(Qt.NoItemFlags)
                self.table.setItem(rc, 2, unu_it)
                # unu_it = QTableWidgetItem()
                # unu_it.setFlags(Qt.NoItemFlags)
                # self.table.setItem(rc, 3, unu_it)
                # self.table.item(rc, 3).setBackground(COLOR_UNUSED)

                img_pixmap = QPixmap(
                    "{}/imgs/partitions/{}.png".format(os.path.dirname(__file__), rc - 4))
                self.prnt.img_label.setPixmap(
                    img_pixmap.scaled(self.prnt.img_label.width(), self.prnt.img_label.height()))
            except Exception:
                pass

    def update_collisions(self, data):
        data_it = QTableWidgetItem(str(data))
        data_it.setFlags(Qt.NoItemFlags)
        self.table.setItem(2, 1, data_it)

    def update_side_time(self, data):
        data_it = QTableWidgetItem(str(round(float(data), 2)))
        data_it.setFlags(Qt.NoItemFlags)
        self.table.setItem(2, 3, data_it)

    def update_msd_current(self, data):
        data_it = QTableWidgetItem(str(round(float(data), 2)))
        data_it.setFlags(Qt.NoItemFlags)
        self.table.setItem(self.table.rowCount() - 1, 1, data_it)

    def update_msd_overall(self, data):
        data_it = QTableWidgetItem(str(round(float(data), 2)))
        data_it.setFlags(Qt.NoItemFlags)
        self.table.setItem(self.table.rowCount() - 1, 2, data_it)

    def update_reformation(self, data):
        data_it = QTableWidgetItem(str(round(float(data), 2)))
        data_it.setFlags(Qt.NoItemFlags)
        self.table.setItem(self.table.rowCount() - 1, 3, data_it)

    def update_times(self, data):
        data_it = QTableWidgetItem(str(round(float(data), 2)))
        data_it.setFlags(Qt.NoItemFlags)
        self.table.setItem(self.table.rowCount() - 1, 1, data_it)

    def update_passes(self, data):
        data_it = QTableWidgetItem(str(round(float(data), 2)))
        data_it.setFlags(Qt.NoItemFlags)
        self.table.setItem(self.table.rowCount() - 1, 2, data_it)

    def collisions_cb(self, data):
        self.update_collisions(data.data)

    def side_time_cb(self, data):
        self.update_side_time(data.data)

    def msd_current_cb(self, data):
        self.update_msd_current(data.data)

    def msd_overall_cb(self, data):
        self.update_msd_overall(data.data)
        self.add_row()

    def reformation_cb(self, data):
        self.update_reformation(data.data)

    def passes_cb(self, data):
        self.update_passes(data.data)

    def times_cb(self, data):
        self.update_times(data.data)
        self.add_row()

    # noinspection PyMethodMayBeStatic
    def final_cb(self, data):
        dds = data.data.split('::')
        if len(dds) == 4:
            string = "Результат: {} \n" \
                     "___________________________ \n" \
                     "Номинации\n" \
                     "Синхронность: {} \n" \
                     "Эффективность: {} \n" \
                     "Скорость: {}".format(*tuple(dds))
        elif len(dds) == 3:
            string = "Результат: {} \n" \
                     "___________________________ \n" \
                     "Номинации\n" \
                     "Точность: {} \n" \
                     "Скорость: {}".format(*tuple(dds))
        else:
            string = "BAD DATA"
        # print(string)
        self.final_string = string
        # noinspection PyUnresolvedReferences
        self.show_msg.emit()

    def show_message(self):
        self.timer.stop()
        self.table.removeRow(self.table.rowCount() - 1)
        QMessageBox.information(self.parent(), "RESULT", self.final_string, QMessageBox.Ok)
