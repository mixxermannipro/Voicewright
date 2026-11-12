#include <gtk/gtk.h>
#include <stdio.h>
#include <string.h>

static void save(const gchar *text, const char *path) {
    FILE *file = fopen(path, "w");
    if (file) {
        fputs(text, file);
        fclose(file);
    }
}

static void entry_changed(GtkEditable *entry, gpointer result_path) {
    save(gtk_entry_get_text(GTK_ENTRY(entry)), result_path);
}

static gboolean key_pressed(GtkWidget *widget, GdkEventKey *event, gpointer result_path) {
    (void)widget;
    if (event->keyval == GDK_KEY_Return || event->keyval == GDK_KEY_KP_Enter) {
        gchar *path = g_strconcat(result_path, ".enter", NULL);
        save("Return was pressed", path);
        g_free(path);
    }
    return FALSE;
}

static void changed(GtkTextBuffer *buffer, gpointer result_path) {
    GtkTextIter start, end;
    gtk_text_buffer_get_bounds(buffer, &start, &end);
    gchar *text = gtk_text_buffer_get_text(buffer, &start, &end, FALSE);
    save(text, result_path);
    g_free(text);
}

int main(int argc, char **argv) {
    gtk_init(&argc, &argv);
    if (argc != 3) return 2;
    save("", argv[1]);
    GtkWidget *window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(window), "External Multiline Probe");
    gtk_window_set_default_size(GTK_WINDOW(window), 600, 300);
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_container_add(GTK_CONTAINER(window), box);
    GtkWidget *view;
    if (!strcmp(argv[2], "multiline") || !strcmp(argv[2], "switch")) {
        view = gtk_text_view_new();
        gtk_text_view_set_accepts_tab(GTK_TEXT_VIEW(view), FALSE);
        GtkTextBuffer *buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(view));
        g_signal_connect(buffer, "changed", G_CALLBACK(changed), argv[1]);
    } else {
        view = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(view), strcmp(argv[2], "password") != 0);
        g_signal_connect(view, "changed", G_CALLBACK(entry_changed), argv[1]);
    }
    gtk_box_pack_start(GTK_BOX(box), view, TRUE, TRUE, 0);
    g_signal_connect(view, "key-press-event", G_CALLBACK(key_pressed), argv[1]);
    if (!strcmp(argv[2], "switch")) {
        GtkWidget *other = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(other), FALSE);
        g_signal_connect(other, "changed", G_CALLBACK(entry_changed), argv[1]);
        gtk_box_pack_start(GTK_BOX(box), other, FALSE, FALSE, 0);
    }
    gtk_widget_show_all(window);
    gtk_widget_grab_focus(view);
    gtk_main();
    return 0;
}
