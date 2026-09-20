<?php
/**
 * Allow authenticated editors to read and write the Rank Math SEO title and
 * meta description through the standard WordPress REST API.
 *
 * Install only when Rank Math is the site's active SEO plugin AND the guide's
 * read-only REST check shows the two fields are not already registered
 * (many recent plugin versions register them out of the box).
 */

defined( 'ABSPATH' ) || exit;

add_action(
	'init',
	static function () {
		$keys = array( 'rank_math_title', 'rank_math_description' );

		foreach ( array( 'post', 'page' ) as $post_type ) {
			foreach ( $keys as $key ) {
				register_post_meta(
					$post_type,
					$key,
					array(
						'type'              => 'string',
						'single'            => true,
						'show_in_rest'      => true,
						'sanitize_callback' => 'sanitize_text_field',
						'auth_callback'     => static function ( $allowed, $meta_key, $post_id ) {
							return current_user_can( 'edit_post', $post_id );
						},
					)
				);
			}
		}
	}
);
