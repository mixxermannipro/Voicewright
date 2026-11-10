#include <gtk/gtk.h>
#include <stdio.h>

static void changed(GtkTextBuffer *buffer, gpointer result_path) {
    GtkTextIter start, end;
    gtk_text_buffer_get_bounds(buffer, &start, &end);
    gchar *text = gtk_text_buffer_get_text(buffer, &start, &end, FALSE);
    FILE *file = fopen(result_path, "w");
    if (file) {
        fputs(text, file);
        fclose(file);
    }
    g_free(text);
}

int main(int argc, char **argv) {
    gtk_init(&argc, &argv);
    if (argc != 2) return 2;
    GtkWidget *window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(window), "External Multiline Probe");
    gtk_window_set_default_size(GTK_WINDOW(window), 600, 300);
    GtkWidget *view = gtk_text_view_new();
    gtk_container_add(GTK_CONTAINER(window), view);
    GtkTextBuffer *buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(view));
    g_signal_connect(buffer, "changed", G_CALLBACK(changed), argv[1]);
    gtk_widget_show_all(window);
    gtk_widget_grab_focus(view);
    gtk_main();
    return 0;
}
