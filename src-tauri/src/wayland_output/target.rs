//! Fail-closed field metadata. Never reads target text or changes accessibility settings.
use ashpd::zbus::{self, Connection, OwnedObjectPath, Proxy};
use std::{collections::HashSet, future::Future, time::Duration};

const ROOT: &str = "/org/a11y/atspi/accessible/root";
const ACCESSIBLE: &str = "org.a11y.atspi.Accessible";
const BUDGET: Duration = Duration::from_millis(600);
const MAX_NODES: usize = 512;
type Object = (String, OwnedObjectPath);

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct Field {
    address: String,
    owner: String,
    path: OwnedObjectPath,
    window: OwnedObjectPath,
    pid: u32,
}

fn state(states: &[u32], index: usize) -> bool {
    states
        .get(index / 32)
        .is_some_and(|word| word & (1 << (index % 32)) != 0)
}

fn safe_field(role: u32, states: &[u32]) -> bool {
    // AT-SPI role TEXT=61 / ENTRY=79. Unknown roles (including terminals and
    // password text) are not equivalent to an editable text field.
    states.len() >= 2
        && matches!(role, 61 | 79)
        && [7, 8, 12, 24, 25, 30]
            .into_iter()
            .all(|bit| state(states, bit))
        && !state(states, 6) // defunct
        && !state(states, 43) // read-only
}

fn bounded<F, Fut, T>(operation: F) -> Option<T>
where
    F: FnOnce() -> Fut + Send,
    Fut: Future<Output = Option<T>>,
    T: Send,
{
    // Calls originate in both sync hotkey callbacks and Tokio workers. A small
    // dedicated runtime avoids nesting block_on inside either caller's runtime.
    std::thread::scope(|scope| {
        scope
            .spawn(move || {
                let runtime = tokio::runtime::Builder::new_current_thread()
                    .enable_all()
                    .build()
                    .ok()?;
                runtime.block_on(async { tokio::time::timeout(BUDGET, operation()).await.ok()? })
            })
            .join()
            .ok()?
    })
}

async fn connect() -> Option<(String, Connection)> {
    let session = Connection::session().await.ok()?;
    let bus = Proxy::new(&session, "org.a11y.Bus", "/org/a11y/bus", "org.a11y.Bus")
        .await
        .ok()?;
    let address: String = bus.call("GetAddress", &()).await.ok()?;
    if !address.starts_with("unix:") {
        return None;
    }
    let connection = zbus::connection::Builder::address(address.as_str())
        .build()
        .await
        .ok()?;
    Some((address, connection))
}

async fn pid(connection: &Connection, owner: &str) -> Option<u32> {
    if !owner.starts_with(':') {
        return None; // Never bind a target to a reassignable well-known name.
    }
    Proxy::new(
        connection,
        "org.freedesktop.DBus",
        "/org/freedesktop/DBus",
        "org.freedesktop.DBus",
    )
    .await
    .ok()?
    .call("GetConnectionUnixProcessID", &(owner,))
    .await
    .ok()
}

async fn metadata(proxy: &Proxy<'_>) -> Option<(u32, Vec<u32>)> {
    let states: Vec<u32> = proxy.call("GetState", &()).await.ok()?;
    let role: u32 = proxy.call("GetRole", &()).await.ok()?;
    Some((role, states))
}

pub(crate) fn capture() -> Option<Field> {
    bounded(|| async {
        let (address, connection) = connect().await?;
        let registry = Proxy::new(&connection, "org.a11y.atspi.Registry", ROOT, ACCESSIBLE)
            .await
            .ok()?;
        let applications: Vec<Object> = registry.call("GetChildren", &()).await.ok()?;
        if applications.len() > MAX_NODES {
            return None;
        }
        let mut found = None;
        for (owner, root) in applications {
            if !owner.starts_with(':') {
                continue;
            }
            let mut queue = vec![(root, None)];
            let mut visited = HashSet::new();
            while let Some((path, mut window)) = queue.pop() {
                if !visited.insert(path.clone()) {
                    continue;
                }
                if visited.len() > MAX_NODES {
                    return None;
                }
                let Ok(proxy) =
                    Proxy::new(&connection, owner.as_str(), path.as_str(), ACCESSIBLE).await
                else {
                    continue;
                };
                let Some((role, states)) = metadata(&proxy).await else {
                    continue;
                };
                if matches!(role, 16 | 23 | 69) {
                    // dialog, frame, window
                    if !state(&states, 1) {
                        continue; // Never search inactive sibling windows.
                    }
                    window = Some(path.clone());
                }
                if state(&states, 12) {
                    // A protected or ambiguous focused node is not permission to
                    // keep searching for a more convenient stale focus flag.
                    if !safe_field(role, &states) || found.is_some() {
                        return None;
                    }
                    found = Some(Field {
                        address: address.clone(),
                        owner: owner.clone(),
                        path: path.clone(),
                        window: window.clone()?,
                        pid: pid(&connection, &owner).await?,
                    });
                }
                let Ok(children): Result<Vec<Object>, _> = proxy.call("GetChildren", &()).await
                else {
                    continue;
                };
                if queue.len() + children.len() > MAX_NODES {
                    return None;
                }
                queue.extend(
                    children
                        .into_iter()
                        .filter_map(|(bus, path)| (bus == owner).then_some((path, window.clone()))),
                );
            }
        }
        found
    })
}

pub(crate) fn unchanged(field: &Field) -> bool {
    let field = field.clone();
    bounded(move || async move {
        let (address, connection) = connect().await?;
        if address != field.address || pid(&connection, &field.owner).await? != field.pid {
            return None;
        }
        let window = Proxy::new(
            &connection,
            field.owner.as_str(),
            field.window.as_str(),
            ACCESSIBLE,
        )
        .await
        .ok()?;
        if !state(&metadata(&window).await?.1, 1) {
            return None;
        }
        let proxy = Proxy::new(
            &connection,
            field.owner.as_str(),
            field.path.as_str(),
            ACCESSIBLE,
        )
        .await
        .ok()?;
        let (role, states) = metadata(&proxy).await?;
        Some(safe_field(role, &states))
    }) == Some(true)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn states() -> Vec<u32> {
        vec![
            (1 << 7) | (1 << 8) | (1 << 12) | (1 << 24) | (1 << 25) | (1 << 30),
            0,
        ]
    }

    #[test]
    fn only_live_focused_editable_text_roles_are_safe() {
        assert!(safe_field(61, &states()));
        assert!(safe_field(79, &states()));
        for role in [0, 40, 60, 67, 999] {
            assert!(!safe_field(role, &states()));
        }
        for bit in [7, 8, 12, 24, 25, 30] {
            let mut current = states();
            current[0] &= !(1 << bit);
            assert!(!safe_field(61, &current));
        }
    }

    #[test]
    fn readonly_defunct_and_missing_metadata_fail_closed() {
        let mut current = states();
        current[1] |= 1 << (43 - 32);
        assert!(!safe_field(61, &current));
        current = states();
        current[0] |= 1 << 6;
        assert!(!safe_field(61, &current));
        assert!(!safe_field(61, &[]));
        assert!(!safe_field(61, &[u32::MAX]));
    }
}
